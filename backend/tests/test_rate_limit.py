from httpx import AsyncClient

from app.config import get_settings

CREDS = {"email": "karim@example.com", "password": "s3cure-password", "display_name": "Karim"}


async def _register(client: AsyncClient) -> None:
    await client.post("/auth/register", json=CREDS)


async def _login(client: AsyncClient, password: str, email: str = CREDS["email"], headers=None):
    return await client.post("/auth/login", json={"email": email, "password": password}, headers=headers)


async def test_login_locks_after_repeated_failures(client: AsyncClient):
    await _register(client)
    limit = get_settings().login_max_failures

    for _ in range(limit):
        response = await _login(client, "wrong-password")
        assert response.status_code == 401

    response = await _login(client, "wrong-password")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_login_attempts"
    assert int(response.headers["retry-after"]) > 0

    # Even the correct password is refused while locked - otherwise the lock is just a hint.
    response = await _login(client, CREDS["password"])
    assert response.status_code == 429


async def test_successful_login_resets_the_counter(client: AsyncClient):
    await _register(client)
    limit = get_settings().login_max_failures

    for _ in range(limit - 1):
        await _login(client, "wrong-password")
    assert (await _login(client, CREDS["password"])).status_code == 200

    for _ in range(limit - 1):
        assert (await _login(client, "wrong-password")).status_code == 401


async def test_unknown_email_is_throttled_the_same_way(client: AsyncClient):
    """No difference between an existing and a non-existing account, so the 429 can't be used to
    enumerate which emails are registered."""
    limit = get_settings().login_max_failures
    for _ in range(limit):
        assert (await _login(client, "x", email="nobody@example.com")).status_code == 401
    assert (await _login(client, "x", email="nobody@example.com")).status_code == 429


async def test_lockout_is_per_email(client: AsyncClient):
    await _register(client)
    limit = get_settings().login_max_failures
    for _ in range(limit):
        await _login(client, "x", email="someone-else@example.com")

    assert (await _login(client, CREDS["password"])).status_code == 200


async def test_trusted_ip_header_separates_clients(client: AsyncClient, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "trusted_client_ip_header", "CF-Connecting-IP")
    await _register(client)

    attacker = {"CF-Connecting-IP": "203.0.113.7"}
    for _ in range(settings.login_max_failures):
        await _login(client, "wrong-password", headers=attacker)
    assert (await _login(client, "wrong-password", headers=attacker)).status_code == 429

    # The real owner on a different IP isn't locked out by someone else guessing.
    owner = {"CF-Connecting-IP": "198.51.100.1"}
    assert (await _login(client, CREDS["password"], headers=owner)).status_code == 200


async def test_per_email_cap_applies_across_ips(client: AsyncClient, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "trusted_client_ip_header", "CF-Connecting-IP")
    monkeypatch.setattr(settings, "login_max_failures_per_email", 6)
    await _register(client)

    for i in range(6):
        await _login(client, "wrong-password", headers={"CF-Connecting-IP": f"203.0.113.{i}"})

    response = await _login(client, "wrong-password", headers={"CF-Connecting-IP": "203.0.113.99"})
    assert response.status_code == 429


def test_stale_buckets_are_swept(monkeypatch):
    """Guessing with endless random emails must not grow the counters forever."""
    from app.auth import rate_limit

    monkeypatch.setattr(rate_limit, "_SWEEP_THRESHOLD", 3)
    clock = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])

    for i in range(3):
        rate_limit.record_failure(f"user{i}@example.com", "1.2.3.4")
    clock[0] += get_settings().login_failure_window_minutes * 60 + 1
    rate_limit.record_failure("fresh@example.com", "1.2.3.4")

    assert set(rate_limit._failures_by_email) == {"fresh@example.com"}

from httpx import AsyncClient

from app.config import get_settings


def _items(response) -> dict[str, dict]:
    return {i["key"]: i for i in response.json()["items"]}


async def test_fresh_account_has_nothing_done(client: AsyncClient, auth_headers: dict):
    response = await client.get("/users/me/setup-status", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["completed"] == 0
    assert body["total"] == len(body["items"])
    assert body["dismissed"] is False
    items = _items(response)
    assert {"first_conversation", "memory", "calendar", "email", "home_assistant", "web_search"} <= set(items)
    assert items["calendar"]["settings_tab"] == "integrations"
    assert items["first_conversation"]["href"] == "/voice"


async def test_items_tick_off_as_the_user_sets_things_up(client: AsyncClient, auth_headers: dict):
    await client.post("/chat/conversations", json={}, headers=auth_headers)
    await client.post("/memory", json={"content": "Ich wohne in Berlin."}, headers=auth_headers)

    response = await client.get("/users/me/setup-status", headers=auth_headers)
    items = _items(response)

    assert items["first_conversation"]["done"] is True
    assert items["memory"]["done"] is True
    assert items["calendar"]["done"] is False
    assert response.json()["completed"] == 2


async def test_push_and_sso_items_only_when_server_supports_them(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    items = _items(await client.get("/users/me/setup-status", headers=auth_headers))
    assert "push" not in items
    assert "sso" not in items

    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub")
    monkeypatch.setattr(settings, "vapid_private_key", "priv")
    monkeypatch.setattr(settings, "oidc_issuer_url", "https://auth.example.com")
    monkeypatch.setattr(settings, "oidc_client_id", "c")
    monkeypatch.setattr(settings, "oidc_client_secret", "s")
    monkeypatch.setattr(settings, "oidc_redirect_uri", "https://x/cb")

    items = _items(await client.get("/users/me/setup-status", headers=auth_headers))
    assert items["push"]["done"] is False
    assert items["sso"]["done"] is False


async def test_dismiss_is_persisted_and_reversible(client: AsyncClient, auth_headers: dict):
    response = await client.put("/users/me/setup-status", json={"dismissed": True}, headers=auth_headers)
    assert response.json()["dismissed"] is True
    assert (await client.get("/users/me/setup-status", headers=auth_headers)).json()["dismissed"] is True

    response = await client.put("/users/me/setup-status", json={"dismissed": False}, headers=auth_headers)
    assert response.json()["dismissed"] is False


async def test_setup_status_requires_auth(client: AsyncClient):
    assert (await client.get("/users/me/setup-status")).status_code == 401

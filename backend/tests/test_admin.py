from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, *, approver_headers: dict | None = None) -> dict:
    """Registers + logs in. Every registration after the first-ever (bootstrap admin) starts
    "pending" and can't log in until approved - pass the admin's headers as `approver_headers`
    for any second-or-later user in a test."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": "s3cure-password", "display_name": "Someone"},
    )
    if approver_headers is not None:
        pending = await client.get("/admin/users/pending", headers=approver_headers)
        user_id = next(u["id"] for u in pending.json()["users"] if u["email"] == email)
        await client.patch(
            f"/admin/users/{user_id}/approval",
            json={"approval_status": "approved"},
            headers=approver_headers,
        )
    login = await client.post("/auth/login", json={"email": email, "password": "s3cure-password"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_first_registered_user_becomes_admin(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"email": "first@example.com", "password": "s3cure-password", "display_name": "First"},
    )
    assert response.status_code == 201
    assert response.json()["is_admin"] is True


async def test_second_registered_user_is_not_admin(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "first@example.com", "password": "s3cure-password", "display_name": "First"},
    )
    second = await client.post(
        "/auth/register",
        json={"email": "second@example.com", "password": "s3cure-password", "display_name": "Second"},
    )
    assert second.json()["is_admin"] is False


async def test_non_admin_cannot_access_admin_endpoints(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")
    non_admin_headers = await _register_and_login(
        client, "regular@example.com", approver_headers=admin_headers
    )

    response = await client.get("/admin/settings", headers=non_admin_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_admin"


async def test_admin_can_get_and_update_settings(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")

    initial = await client.get("/admin/settings", headers=admin_headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "registration_open": True,
        "system_paused": False,
        "system_paused_message": None,
    }

    updated = await client.patch(
        "/admin/settings", json={"registration_open": False}, headers=admin_headers
    )
    assert updated.status_code == 200
    assert updated.json()["registration_open"] is False
    assert updated.json()["system_paused"] is False  # untouched fields stay as-is


async def test_registration_closed_blocks_new_registrations(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")
    await client.patch("/admin/settings", json={"registration_open": False}, headers=admin_headers)

    blocked = await client.post(
        "/auth/register",
        json={"email": "latecomer@example.com", "password": "s3cure-password", "display_name": "Late"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "registration_closed"


async def test_system_paused_blocks_chat_but_admin_can_still_unpause(client: AsyncClient, monkeypatch):
    from app.services import ollama_client

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Hallo!", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    admin_headers = await _register_and_login(client, "admin@example.com")
    await client.patch(
        "/admin/settings",
        json={"system_paused": True, "system_paused_message": "Wartungsarbeiten"},
        headers=admin_headers,
    )

    created = await client.post("/chat/conversations", json={}, headers=admin_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Hallo"},
        headers=admin_headers,
    )
    assert sent.status_code == 503
    assert sent.json()["error"]["code"] == "system_paused"
    assert sent.json()["error"]["message"] == "Wartungsarbeiten"

    # The admin themself must still be able to reach the settings endpoint to unpause -
    # a paused system must never lock its own admin out.
    still_reachable = await client.get("/admin/settings", headers=admin_headers)
    assert still_reachable.status_code == 200

    # Login must also keep working while paused - otherwise nobody could even get a token
    # to unpause the system in a fresh session.
    login_still_works = await client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "s3cure-password"}
    )
    assert login_still_works.status_code == 200

    unpaused = await client.patch("/admin/settings", json={"system_paused": False}, headers=admin_headers)
    assert unpaused.json()["system_paused"] is False

    resumed = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Nochmal"},
        headers=admin_headers,
    )
    assert resumed.status_code == 200


async def test_admin_users_list(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")
    # /admin/users lists everyone regardless of approval status - no need to log the second
    # user in (and therefore no need to approve them) just to appear in this list.
    await client.post(
        "/auth/register",
        json={"email": "regular@example.com", "password": "s3cure-password", "display_name": "Regular"},
    )

    response = await client.get("/admin/users", headers=admin_headers)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()["users"]}
    assert emails == {"admin@example.com", "regular@example.com"}


async def test_second_registered_user_starts_pending_and_cannot_login(client: AsyncClient):
    await _register_and_login(client, "admin@example.com")
    register = await client.post(
        "/auth/register",
        json={"email": "pending@example.com", "password": "s3cure-password", "display_name": "Pending"},
    )
    assert register.json()["approval_status"] == "pending"

    login = await client.post(
        "/auth/login", json={"email": "pending@example.com", "password": "s3cure-password"}
    )
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "registration_pending"


async def test_admin_can_approve_pending_user(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")
    await client.post(
        "/auth/register",
        json={"email": "newbie@example.com", "password": "s3cure-password", "display_name": "Newbie"},
    )

    pending = await client.get("/admin/users/pending", headers=admin_headers)
    assert pending.status_code == 200
    assert [u["email"] for u in pending.json()["users"]] == ["newbie@example.com"]
    user_id = pending.json()["users"][0]["id"]

    approved = await client.patch(
        f"/admin/users/{user_id}/approval",
        json={"approval_status": "approved"},
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["users"] == []  # no longer pending

    login = await client.post(
        "/auth/login", json={"email": "newbie@example.com", "password": "s3cure-password"}
    )
    assert login.status_code == 200


async def test_admin_can_decline_pending_user(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")
    await client.post(
        "/auth/register",
        json={"email": "nope@example.com", "password": "s3cure-password", "display_name": "Nope"},
    )
    pending = await client.get("/admin/users/pending", headers=admin_headers)
    user_id = pending.json()["users"][0]["id"]

    declined = await client.patch(
        f"/admin/users/{user_id}/approval",
        json={"approval_status": "declined"},
        headers=admin_headers,
    )
    assert declined.status_code == 200

    login = await client.post(
        "/auth/login", json={"email": "nope@example.com", "password": "s3cure-password"}
    )
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "registration_declined"


async def test_non_admin_cannot_approve_users(client: AsyncClient):
    admin_headers = await _register_and_login(client, "admin@example.com")
    non_admin_headers = await _register_and_login(
        client, "regular@example.com", approver_headers=admin_headers
    )
    response = await client.patch(
        "/admin/users/some-id/approval",
        json={"approval_status": "approved"},
        headers=non_admin_headers,
    )
    assert response.status_code == 403

from datetime import datetime, timezone

from httpx import AsyncClient

from app.services import ollama_client


def _fake_chat_with_tool_call(tool_name: str, arguments: dict, final_reply: str):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": tool_name, "arguments": arguments}}],
            }
        return {"role": "assistant", "content": final_reply, "tool_calls": []}

    return fake_chat, calls


async def _send_via_tool(client: AsyncClient, auth_headers: dict, monkeypatch, tool_name, arguments, final_reply):
    fake_chat, calls = _fake_chat_with_tool_call(tool_name, arguments, final_reply)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "irrelevant, ollama is mocked"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    assert calls["n"] == 2
    return sent.json()["message"]


async def test_set_timer_via_chat_tool_call(client: AsyncClient, auth_headers: dict, monkeypatch):
    message = await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 300, "label": "Nudeln"}, "Timer läuft."
    )
    result = message["tool_calls"][0]["result"]
    assert result["label"] == "Nudeln"
    ends_at = datetime.fromisoformat(result["ends_at"])
    assert ends_at > datetime.now(timezone.utc)


async def test_list_timers_endpoint_reflects_set_timer(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 60, "label": "Eier"}, "Ok."
    )

    listed = await client.get("/timers", headers=auth_headers)
    assert listed.status_code == 200
    timers = listed.json()["timers"]
    assert len(timers) == 1
    assert timers[0]["label"] == "Eier"


async def test_list_timers_via_chat_tool_call(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 600, "label": "Wäsche"}, "Ok."
    )
    message = await _send_via_tool(client, auth_headers, monkeypatch, "list_timers", {}, "Ein Timer läuft.")
    result = message["tool_calls"][0]["result"]
    assert len(result) == 1
    assert result[0]["label"] == "Wäsche"
    assert result[0]["remaining_seconds"] > 0


async def test_cancel_timer_via_endpoint_then_excluded_from_list(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 120, "label": "Anruf"}, "Ok."
    )
    listed = await client.get("/timers", headers=auth_headers)
    timer_id = listed.json()["timers"][0]["id"]

    cancelled = await client.post(f"/timers/{timer_id}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200

    listed_after = await client.get("/timers", headers=auth_headers)
    assert listed_after.json()["timers"] == []


async def test_cancel_timer_via_chat_tool_call(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 90, "label": "Kaffee"}, "Ok."
    )
    listed = await client.get("/timers", headers=auth_headers)
    timer_id = listed.json()["timers"][0]["id"]

    message = await _send_via_tool(
        client, auth_headers, monkeypatch, "cancel_timer", {"timer_id": timer_id}, "Abgebrochen."
    )
    result = message["tool_calls"][0]["result"]
    assert result == {"id": timer_id, "cancelled": True}


async def test_cancel_unknown_timer_returns_404(client: AsyncClient, auth_headers: dict):
    response = await client.post("/timers/does-not-exist/cancel", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "timer_not_found"


async def test_invalid_timer_duration_surfaces_as_tool_error(client: AsyncClient, auth_headers: dict, monkeypatch):
    message = await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 0}, "Das ging nicht."
    )
    result = message["tool_calls"][0]["result"]
    assert "duration_seconds" in result["error"]


async def test_timers_are_scoped_per_user(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _send_via_tool(
        client, auth_headers, monkeypatch, "set_timer", {"duration_seconds": 60, "label": "mine"}, "Ok."
    )

    await client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "s3cure-password", "display_name": "Other"},
    )
    other_login = await client.post(
        "/auth/login", json={"email": "other@example.com", "password": "s3cure-password"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    listed = await client.get("/timers", headers=other_headers)
    assert listed.json()["timers"] == []

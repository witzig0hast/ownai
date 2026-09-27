from httpx import AsyncClient

from app.services import ollama_client


async def test_new_conversation_defaults_to_general_skill(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    assert created.json()["skill"] == "general"


async def test_list_skills(client: AsyncClient, auth_headers: dict):
    response = await client.get("/chat/skills", headers=auth_headers)
    assert response.status_code == 200
    keys = {s["key"] for s in response.json()["skills"]}
    assert {"general", "home", "organize"} <= keys


async def test_switch_conversation_skill(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    updated = await client.patch(
        f"/chat/conversations/{conversation_id}", json={"skill": "home"}, headers=auth_headers
    )
    assert updated.status_code == 200
    assert updated.json()["skill"] == "home"


async def test_switch_to_unknown_skill_is_rejected(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    response = await client.patch(
        f"/chat/conversations/{conversation_id}", json={"skill": "does-not-exist"}, headers=auth_headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_skill"


async def test_home_skill_only_offers_its_own_tools(client: AsyncClient, auth_headers: dict, monkeypatch):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    await client.patch(f"/chat/conversations/{conversation_id}", json={"skill": "home"}, headers=auth_headers)

    seen_tool_names: list[str] = []

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        seen_tool_names.extend(t["function"]["name"] for t in (tools or []))
        return {"role": "assistant", "content": "Ok.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await client.post(
        f"/chat/conversations/{conversation_id}/messages", json={"content": "Hi"}, headers=auth_headers
    )
    assert set(seen_tool_names) == {
        "home_assistant_list_entities",
        "home_assistant_call_service",
        "set_timer",
        "list_timers",
        "cancel_timer",
    }


async def test_home_skill_refuses_out_of_skill_tool_call(client: AsyncClient, auth_headers: dict, monkeypatch):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    await client.patch(f"/chat/conversations/{conversation_id}", json={"skill": "home"}, headers=auth_headers)

    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "send_email", "arguments": {}}}],
            }
        return {"role": "assistant", "content": "Ging nicht.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine E-Mail"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert "nicht verfügbar" in result["error"]

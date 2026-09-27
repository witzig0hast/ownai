from httpx import AsyncClient

from app.services import ollama_client


async def test_create_list_delete_memory(client: AsyncClient, auth_headers: dict):
    created = await client.post("/memory", json={"content": "Mag keine Zwiebeln"}, headers=auth_headers)
    assert created.status_code == 201
    memory_id = created.json()["id"]

    listed = await client.get("/memory", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["memories"]) == 1
    assert listed.json()["memories"][0]["content"] == "Mag keine Zwiebeln"

    deleted = await client.delete(f"/memory/{memory_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed_again = await client.get("/memory", headers=auth_headers)
    assert listed_again.json()["memories"] == []


async def test_delete_foreign_memory_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/memory/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_memories_are_injected_into_system_prompt(client: AsyncClient, auth_headers: dict, monkeypatch):
    await client.post("/memory", json={"content": "Mag keine Zwiebeln"}, headers=auth_headers)

    seen_system_prompts = []

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        seen_system_prompts.append(messages[0]["content"])
        return {"role": "assistant", "content": "Ok.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    await client.post(
        f"/chat/conversations/{conversation_id}/messages", json={"content": "Hi"}, headers=auth_headers
    )

    assert "Mag keine Zwiebeln" in seen_system_prompts[0]


async def test_chat_tool_remembers_and_forgets_facts(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "remember_fact", "arguments": {"content": "Fährt einen Tesla"}}}
                ],
            }
        return {"role": "assistant", "content": "Gemerkt.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Ich fahre einen Tesla"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["content"] == "Fährt einen Tesla"

    listed = await client.get("/memory", headers=auth_headers)
    assert listed.json()["memories"][0]["content"] == "Fährt einen Tesla"

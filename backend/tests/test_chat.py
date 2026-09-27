from httpx import AsyncClient

from app.services import ollama_client


async def test_conversation_and_plain_reply(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Hallo! Wie kann ich helfen?", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={"title": "Erstes Gespräch"}, headers=auth_headers)
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    listed = await client.get("/chat/conversations", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["conversations"]) == 1

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Hallo"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    message = sent.json()["message"]
    assert message["role"] == "assistant"
    assert message["content"] == "Hallo! Wie kann ich helfen?"
    assert message["tool_calls"] is None

    history = await client.get(f"/chat/conversations/{conversation_id}/messages", headers=auth_headers)
    assert history.status_code == 200
    roles = [m["role"] for m in history.json()["messages"]]
    assert roles == ["user", "assistant"]


async def test_chat_turn_executes_tool_call_then_answers(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "calendar_list_events", "arguments": {}}}],
            }
        return {"role": "assistant", "content": "Du hast heute nichts im Kalender.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    async def fake_handler(db, user, conversation, arguments):  # noqa: ARG001
        return []

    from app.agent import tools as agent_tools

    # orchestrator.py did `from app.agent.tools import TOOL_HANDLERS`, so it holds a reference to this same
    # dict object — mutate it in place (monkeypatch.setitem, auto-restored) rather than reassigning the module
    # attribute, which orchestrator's already-bound name would not pick up.
    monkeypatch.setitem(agent_tools.TOOL_HANDLERS, "calendar_list_events", fake_handler)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Habe ich heute noch etwas vor?"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    message = sent.json()["message"]
    assert message["content"] == "Du hast heute nichts im Kalender."
    assert message["tool_calls"] == [{"tool": "calendar_list_events", "arguments": {}, "result": []}]
    assert calls["n"] == 2


async def test_streaming_not_yet_implemented(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    response = await client.post(
        f"/chat/conversations/{conversation_id}/messages?stream=true",
        json={"content": "Hi"},
        headers=auth_headers,
    )
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "not_implemented"


async def test_messages_for_foreign_conversation_are_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get("/chat/conversations/does-not-exist/messages", headers=auth_headers)
    assert response.status_code == 404


async def test_first_exchange_auto_generates_title(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Klar, helfe ich gerne!", "tool_calls": []}

    async def fake_generate_title(user_message, assistant_reply):  # noqa: ARG001
        return "Hilfe bei Python"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)
    monkeypatch.setattr(ollama_client, "generate_title", fake_generate_title)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    assert created.json()["title"] is None

    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Hilf mir mit Python"},
        headers=auth_headers,
    )

    listed = await client.get("/chat/conversations", headers=auth_headers)
    assert listed.json()["conversations"][0]["title"] == "Hilfe bei Python"


async def test_explicit_title_is_never_overwritten_by_auto_title(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Ok!", "tool_calls": []}

    async def fake_generate_title(user_message, assistant_reply):  # noqa: ARG001
        return "Sollte nie ankommen"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)
    monkeypatch.setattr(ollama_client, "generate_title", fake_generate_title)

    created = await client.post("/chat/conversations", json={"title": "Mein Titel"}, headers=auth_headers)
    conversation_id = created.json()["id"]

    await client.post(
        f"/chat/conversations/{conversation_id}/messages", json={"content": "Hi"}, headers=auth_headers
    )

    listed = await client.get("/chat/conversations", headers=auth_headers)
    assert listed.json()["conversations"][0]["title"] == "Mein Titel"


async def test_rename_conversation(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    renamed = await client.patch(
        f"/chat/conversations/{conversation_id}", json={"title": "Neuer Titel"}, headers=auth_headers
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Neuer Titel"


async def test_archive_hides_conversation_from_default_list(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={"title": "Archiv mich"}, headers=auth_headers)
    conversation_id = created.json()["id"]

    archived = await client.patch(
        f"/chat/conversations/{conversation_id}", json={"archived": True}, headers=auth_headers
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] is True

    default_list = await client.get("/chat/conversations", headers=auth_headers)
    assert default_list.json()["conversations"] == []

    with_archived = await client.get("/chat/conversations?include_archived=true", headers=auth_headers)
    assert len(with_archived.json()["conversations"]) == 1

    unarchived = await client.patch(
        f"/chat/conversations/{conversation_id}", json={"archived": False}, headers=auth_headers
    )
    assert unarchived.json()["archived"] is False


async def test_delete_conversation_removes_it(client: AsyncClient, auth_headers: dict):
    created = await client.post("/chat/conversations", json={"title": "Weg damit"}, headers=auth_headers)
    conversation_id = created.json()["id"]

    deleted = await client.delete(f"/chat/conversations/{conversation_id}", headers=auth_headers)
    assert deleted.status_code == 204

    gone = await client.get(f"/chat/conversations/{conversation_id}/messages", headers=auth_headers)
    assert gone.status_code == 404


async def test_warmup_calls_ollama_and_ignores_failure(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_warmup():
        calls["n"] += 1

    monkeypatch.setattr(ollama_client, "warmup", fake_warmup)

    response = await client.post("/chat/warmup", headers=auth_headers)
    assert response.status_code == 204
    assert calls["n"] == 1

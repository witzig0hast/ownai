from httpx import AsyncClient

from app.services import ollama_client
from app.services.ollama_client import OllamaError


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


async def test_empty_model_reply_gets_a_placeholder_instead_of_a_blank_bubble(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """A local model occasionally returns content="" with no tool_calls at all - a genuine 200
    response, not an error. Saving/showing that as-is renders a blank message bubble that looks
    like a silent failure; there must be a short, honest fallback instead."""

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Hallo"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    content = sent.json()["message"]["content"]
    assert content.strip() != ""


async def test_internal_api_urls_are_stripped_from_reply(client: AsyncClient, auth_headers: dict, monkeypatch):
    """Local models sometimes ignore the "never mention tool-result URLs" instruction and echo
    a create_file download_url back in their reply - this must never leak through, especially
    since Voice would otherwise read the raw path aloud."""

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {
            "role": "assistant",
            "content": (
                "Ich habe die Datei erstellt: /api/v1/chat/conversations/abc-123/files/def-456 "
                "Lass es mich wissen, falls du noch etwas brauchst."
            ),
            "tool_calls": [],
        }

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schreib mir eine Datei"},
        headers=auth_headers,
    )
    content = sent.json()["message"]["content"]
    assert "/api/v1/" not in content
    assert "Ich habe die Datei erstellt:" in content
    assert "Lass es mich wissen" in content


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


async def test_tool_call_missing_argument_gets_actionable_error(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """A tool handler indexes required arguments (arguments["foo"]), so a model that omits one
    raises a plain KeyError - str(KeyError) is just the quoted key name ("'foo'"), a cryptic
    message that previously confused the model into relaying it verbatim instead of retrying
    with a complete call. The error text now has to actually explain what's wrong."""
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                # Missing "subject" and "body" - what the reported bug looked like in practice.
                "tool_calls": [{"function": {"name": "send_email", "arguments": {"to": "x@example.com"}}}],
            }
        return {"role": "assistant", "content": "Ok, hier ist die vollständige E-Mail.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine Test-Mail"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    tool_calls = sent.json()["message"]["tool_calls"]
    assert tool_calls[0]["tool"] == "send_email"
    error = tool_calls[0]["result"]["error"]
    assert "subject" in error
    assert "send_email" in error
    assert error != "'subject'"  # the old, unhelpful raw KeyError text
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


async def test_unreachable_ollama_surfaces_as_llm_unavailable_and_is_logged(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """An unreachable/too-slow Ollama previously bubbled up as a bare, unhandled 500 - now it's a
    clear 503 the frontend can show, and a "chat" log entry the user can see themselves in
    Settings -> Logs instead of needing another debugging session for it."""

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        raise OllamaError("Ollama request failed: timed out")

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Hallo"},
        headers=auth_headers,
    )
    assert sent.status_code == 503
    assert sent.json()["error"]["code"] == "llm_unavailable"

    logs = await client.get("/logs?category=chat", headers=auth_headers)
    entries = logs.json()["logs"]
    assert len(entries) == 1
    assert entries[0]["level"] == "error"
    assert "timed out" in entries[0]["detail"]


async def test_old_history_is_dropped_from_the_prompt_but_kept_in_the_ui(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """MAX_HISTORY_MESSAGES_IN_PROMPT caps the prompt so a long-running conversation doesn't keep
    getting slower turn after turn - but the user must still see their full history via GET
    .../messages, only what's sent to Ollama is windowed."""
    from app.agent import orchestrator

    monkeypatch.setattr(orchestrator, "MAX_HISTORY_MESSAGES_IN_PROMPT", 2)

    seen_message_counts = []

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        seen_message_counts.append(len(messages))
        return {"role": "assistant", "content": "Ok.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    for i in range(4):
        await client.post(
            f"/chat/conversations/{conversation_id}/messages",
            json={"content": f"Nachricht {i}"},
            headers=auth_headers,
        )

    # 8 user+assistant messages exist, but each call only ever saw the system prompt + the
    # last 2 history messages (not the full, ever-growing history).
    assert all(count <= 3 for count in seen_message_counts)

    history = await client.get(f"/chat/conversations/{conversation_id}/messages", headers=auth_headers)
    assert len(history.json()["messages"]) == 8

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

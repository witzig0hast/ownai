from httpx import AsyncClient

from app.services import ollama_client


async def test_spawn_subagent_returns_answer_and_steps(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            # Parent turn: delegate to a subagent.
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "spawn_subagent", "arguments": {"task": "Liste heutige Termine"}}}
                ],
            }
        if calls["n"] == 2:
            # Subagent's own first turn: it calls a tool itself.
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "calendar_list_events", "arguments": {}}}],
            }
        if calls["n"] == 3:
            # Subagent's final answer.
            return {"role": "assistant", "content": "Keine Termine heute.", "tool_calls": []}
        # Parent's final answer, after getting the subagent's result back.
        return {"role": "assistant", "content": "Laut Sub-Agent: keine Termine heute.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    from app.agent import tools as agent_tools

    async def fake_calendar_handler(db, user, conversation, arguments):  # noqa: ARG001
        return []

    monkeypatch.setitem(agent_tools.TOOL_HANDLERS, "calendar_list_events", fake_calendar_handler)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Bitte prüfe meinen Kalender über einen Sub-Agenten"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    message = sent.json()["message"]
    assert message["content"] == "Laut Sub-Agent: keine Termine heute."

    subagent_call = message["tool_calls"][0]
    assert subagent_call["tool"] == "spawn_subagent"
    assert subagent_call["result"]["answer"] == "Keine Termine heute."
    assert subagent_call["result"]["steps"] == [
        {"tool": "calendar_list_events", "arguments": {}, "result": []}
    ]
    assert calls["n"] == 4


async def test_subagent_cannot_spawn_further_subagents(client: AsyncClient, auth_headers: dict, monkeypatch):
    """The subagent's own loop is never offered spawn_subagent - verify the tool schema list
    passed to its inner ollama_client.chat call never contains it."""
    seen_tool_names_per_call: list[list[str]] = []
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        seen_tool_names_per_call.append([t["function"]["name"] for t in (tools or [])])
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "spawn_subagent", "arguments": {"task": "Irgendwas"}}}],
            }
        if calls["n"] == 2:
            # This is the subagent's own inner call - spawn_subagent must not be in `tools` here.
            return {"role": "assistant", "content": "Erledigt.", "tool_calls": []}
        return {"role": "assistant", "content": "Fertig.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Nutze einen Sub-Agenten"},
        headers=auth_headers,
    )
    assert calls["n"] == 3
    # Call index 0 = parent turn (has spawn_subagent), index 1 = subagent's own inner call.
    assert "spawn_subagent" in seen_tool_names_per_call[0]
    assert "spawn_subagent" not in seen_tool_names_per_call[1]


async def test_subagent_respects_conversation_skill_restriction(client: AsyncClient, auth_headers: dict, monkeypatch):
    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    # "home" skill's tool_names don't include spawn_subagent, so it's never offered to the model
    # at all in that conversation - confirmed by the general skill-restriction tests already.
    # Here we confirm a subagent run itself only ever offers the skill's allowed tools.
    await client.patch(f"/chat/conversations/{conversation_id}", json={"skill": "organize"}, headers=auth_headers)

    seen_tool_names_per_call: list[list[str]] = []
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        seen_tool_names_per_call.append([t["function"]["name"] for t in (tools or [])])
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "spawn_subagent", "arguments": {"task": "Schreib etwas"}}}],
            }
        if calls["n"] == 2:
            return {"role": "assistant", "content": "Erledigt.", "tool_calls": []}
        return {"role": "assistant", "content": "Fertig.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Nutze einen Sub-Agenten"},
        headers=auth_headers,
    )
    # "organize" skill only allows calendar/create_file/send_email tools.
    assert set(seen_tool_names_per_call[1]) == {
        "calendar_list_events",
        "calendar_create_event",
        "create_file",
        "send_email",
    }

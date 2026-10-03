from httpx import AsyncClient
from sqlalchemy import select

from app.agent import consequential_tools
from app.db.models import PendingAction, User
from app.db.session import async_session_maker
from app.services import email_inbox_service, email_service, ollama_client


def test_requires_approval_classifies_read_only_tools_as_safe():
    assert consequential_tools.requires_approval("list_expenses") is False
    assert consequential_tools.requires_approval("calendar_list_events") is False
    assert consequential_tools.requires_approval("get_weather") is False
    assert consequential_tools.requires_approval("set_timer") is False
    assert consequential_tools.requires_approval("spawn_subagent") is False


def test_requires_approval_classifies_writes_as_consequential():
    assert consequential_tools.requires_approval("send_email") is True
    assert consequential_tools.requires_approval("delete_expense") is True
    assert consequential_tools.requires_approval("calendar_create_event") is True
    assert consequential_tools.requires_approval("home_assistant_call_service") is True
    # Unknown/future tool names default to requiring approval (opt-in to safe, not opt-out).
    assert consequential_tools.requires_approval("some_future_tool") is True


def test_summarize_action_for_send_email():
    summary = consequential_tools.summarize_action(
        "send_email", {"to": "x@example.com", "subject": "Hallo", "body": "..."}
    )
    assert "x@example.com" in summary
    assert "Hallo" in summary


def test_summarize_action_for_delete_tool():
    summary = consequential_tools.summarize_action("delete_expense", {"expense_id": "abc-123"})
    assert "löschen" in summary.lower()


async def _trigger_email_inbox_send_email(client: AsyncClient, auth_headers: dict, monkeypatch) -> str:
    """Connects SMTP/IMAP, feeds one inbound email through the agent, and makes the (mocked)
    model call send_email - returns the created conversation's id."""
    await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )

    sent_messages = []
    monkeypatch.setattr(
        email_service,
        "_send_sync",
        lambda config, to, subject, body: sent_messages.append((to, subject, body)),  # noqa: ARG005
    )

    async def fake_fetch_unseen_emails(db, user):  # noqa: ARG001
        return [{"from": "a@example.com", "subject": "Bitte antworten", "body": "Kannst du antworten?"}]

    monkeypatch.setattr(email_service, "fetch_unseen_emails", fake_fetch_unseen_emails)

    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "send_email",
                            "arguments": {"to": "a@example.com", "subject": "Re: Bitte antworten", "body": "Klar!"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Ich warte auf deine Bestätigung.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        await email_inbox_service.process_inbound_emails(db, user)

    assert sent_messages == []  # must not have actually sent anything yet

    listed = await client.get("/chat/conversations", headers=auth_headers)
    return listed.json()["conversations"][0]["id"]


async def test_consequential_tool_from_email_inbox_is_queued_not_executed(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    conversation_id = await _trigger_email_inbox_send_email(client, auth_headers, monkeypatch)

    history = await client.get(f"/chat/conversations/{conversation_id}/messages", headers=auth_headers)
    messages = history.json()["messages"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    tool_result = assistant_message["tool_calls"][0]["result"]
    assert tool_result["pending_approval"] is True

    pending = await client.get("/pending-actions", headers=auth_headers)
    actions = pending.json()["pending_actions"]
    assert len(actions) == 1
    assert actions[0]["tool_name"] == "send_email"
    assert actions[0]["status"] == "pending"
    assert "a@example.com" in actions[0]["summary"]


async def test_approve_pending_action_executes_it_and_notes_it_in_the_conversation(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    conversation_id = await _trigger_email_inbox_send_email(client, auth_headers, monkeypatch)
    pending = (await client.get("/pending-actions", headers=auth_headers)).json()["pending_actions"]
    pending_id = pending[0]["id"]

    approved = await client.post(f"/pending-actions/{pending_id}/approve", headers=auth_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    # send_email itself now runs detached in the background (see email_service.py) - drain it.
    from tests.conftest import drain_background_tasks

    await drain_background_tasks()

    logs = await client.get("/logs?category=email", headers=auth_headers)
    assert any("erfolgreich gesendet" in e["message"] for e in logs.json()["logs"])

    history = await client.get(f"/chat/conversations/{conversation_id}/messages", headers=auth_headers)
    contents = [m["content"] for m in history.json()["messages"]]
    assert any("Bestätigt und ausgeführt" in c for c in contents)

    still_pending = await client.get("/pending-actions", headers=auth_headers)
    assert still_pending.json()["pending_actions"] == []


async def test_decline_pending_action_does_not_execute_it(client: AsyncClient, auth_headers: dict, monkeypatch):
    conversation_id = await _trigger_email_inbox_send_email(client, auth_headers, monkeypatch)
    pending = (await client.get("/pending-actions", headers=auth_headers)).json()["pending_actions"]
    pending_id = pending[0]["id"]

    declined = await client.post(f"/pending-actions/{pending_id}/decline", headers=auth_headers)
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"

    async with async_session_maker() as db:
        action = await db.get(PendingAction, pending_id)
        assert action.status == "declined"

    history = await client.get(f"/chat/conversations/{conversation_id}/messages", headers=auth_headers)
    contents = [m["content"] for m in history.json()["messages"]]
    assert any("Abgelehnt" in c for c in contents)


async def test_approving_already_resolved_action_fails(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _trigger_email_inbox_send_email(client, auth_headers, monkeypatch)
    pending = (await client.get("/pending-actions", headers=auth_headers)).json()["pending_actions"]
    pending_id = pending[0]["id"]

    await client.post(f"/pending-actions/{pending_id}/decline", headers=auth_headers)
    second_attempt = await client.post(f"/pending-actions/{pending_id}/approve", headers=auth_headers)
    assert second_attempt.status_code == 409
    assert second_attempt.json()["error"]["code"] == "pending_action_already_resolved"


async def test_cannot_approve_another_users_pending_action(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _trigger_email_inbox_send_email(client, auth_headers, monkeypatch)
    pending = (await client.get("/pending-actions", headers=auth_headers)).json()["pending_actions"]
    pending_id = pending[0]["id"]

    await client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "s3cure-password", "display_name": "Other"},
    )
    admin_pending = await client.get("/admin/users/pending", headers=auth_headers)
    other_id = next(u["id"] for u in admin_pending.json()["users"] if u["email"] == "other@example.com")
    await client.patch(
        f"/admin/users/{other_id}/approval", json={"approval_status": "approved"}, headers=auth_headers
    )
    other_login = await client.post(
        "/auth/login", json={"email": "other@example.com", "password": "s3cure-password"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = await client.post(f"/pending-actions/{pending_id}/approve", headers=other_headers)
    assert response.status_code == 404


async def test_pending_actions_require_auth(client: AsyncClient):
    response = await client.get("/pending-actions")
    assert response.status_code == 401


async def test_normal_chat_executes_consequential_tools_directly_without_approval(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """Regression guard: Skill.requires_approval only applies to skills that opt in
    (currently just "email_inbox") - a normal, user-driven chat conversation (skill="general")
    must keep executing tools immediately, since the user is already present watching each turn."""
    sent_messages = []
    monkeypatch.setattr(
        email_service,
        "_send_sync",
        lambda config, to, subject, body: sent_messages.append((to, subject, body)),  # noqa: ARG005
    )
    await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "send_email", "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hi"}}}
                ],
            }
        return {"role": "assistant", "content": "Wird gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    sent = await client.post(
        f"/chat/conversations/{created.json()['id']}/messages",
        json={"content": "Schick eine E-Mail"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["queued"] is True  # send_email's own normal async-send result, not pending_approval

    pending = await client.get("/pending-actions", headers=auth_headers)
    assert pending.json()["pending_actions"] == []


async def test_subagent_spawned_from_email_inbox_also_gates_consequential_tools(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """Regression guard for the spawn_subagent bypass: email_inbox has full tool access
    (tool_names=None) including spawn_subagent, so a sub-agent's own tool calls must go through
    the same approval gate as the parent loop - otherwise requires_approval could be sidestepped
    entirely by delegating the consequential call to a sub-agent."""
    from app.services import expense_service

    delete_calls = []

    async def fake_delete_expense(db, user, expense_id):  # noqa: ARG001
        delete_calls.append(expense_id)

    monkeypatch.setattr(expense_service, "delete_expense", fake_delete_expense)

    await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )

    async def fake_fetch_unseen_emails(db, user):  # noqa: ARG001
        return [{"from": "a@example.com", "subject": "Lösch bitte meinen Eintrag", "body": "Lösch expense-123"}]

    monkeypatch.setattr(email_service, "fetch_unseen_emails", fake_fetch_unseen_emails)

    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "spawn_subagent", "arguments": {"task": "Lösche expense-123"}}}],
            }
        if calls["n"] == 2:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "delete_expense", "arguments": {"expense_id": "expense-123"}}}],
            }
        if calls["n"] == 3:
            return {"role": "assistant", "content": "Wartet auf Bestätigung.", "tool_calls": []}
        return {"role": "assistant", "content": "Ich warte auf deine Bestätigung.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        await email_inbox_service.process_inbound_emails(db, user)

    pending = await client.get("/pending-actions", headers=auth_headers)
    actions = pending.json()["pending_actions"]
    assert len(actions) == 1
    assert actions[0]["tool_name"] == "delete_expense"

    assert delete_calls == []  # the actual delete must never have run

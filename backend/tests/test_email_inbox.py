from httpx import AsyncClient
from sqlalchemy import select

from app.agent.skills import SKILLS, is_valid_skill_key, public_skills
from app.db.models import Conversation, User
from app.db.session import async_session_maker
from app.services import email_inbox_service, email_service, ollama_client, scheduler


async def _connect_smtp_and_imap(client: AsyncClient, auth_headers: dict) -> None:
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
    await client.post(
        "/integrations/email/imap",
        json={"imap_host": "imap.example.com", "imap_port": 993, "imap_username": "karim", "imap_password": "s3cret"},
        headers=auth_headers,
    )


def test_email_inbox_skill_is_not_publicly_selectable():
    assert "email_inbox" in SKILLS
    assert "email_inbox" not in {s.key for s in public_skills()}
    assert is_valid_skill_key("email_inbox") is False
    assert is_valid_skill_key("general") is True


async def test_process_inbound_emails_creates_a_conversation_via_the_normal_agent_loop(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """The inbound-email agent must reuse run_turn (the exact same turn logic as a normal chat
    message) rather than a separate code path - this proves that end to end: a fetched email
    becomes a real Conversation (skill="email_inbox") with a user message (the formatted email)
    and an assistant reply, visible like any other conversation in the Chat UI."""
    await _connect_smtp_and_imap(client, auth_headers)

    async def fake_fetch_unseen_emails(db, user):  # noqa: ARG001
        return [{"from": "Absender <a@example.com>", "subject": "Testbetreff", "body": "Hallo, bitte antworte kurz."}]

    monkeypatch.setattr(email_service, "fetch_unseen_emails", fake_fetch_unseen_emails)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Verstanden, ich kümmere mich darum.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        processed = await email_inbox_service.process_inbound_emails(db, user)

    assert processed == 1

    listed = await client.get("/chat/conversations", headers=auth_headers)
    conversations = listed.json()["conversations"]
    assert len(conversations) == 1
    assert conversations[0]["title"] == "E-Mail: Testbetreff"
    assert conversations[0]["skill"] == "email_inbox"

    history = await client.get(
        f"/chat/conversations/{conversations[0]['id']}/messages", headers=auth_headers
    )
    messages = history.json()["messages"]
    assert messages[0]["role"] == "user"
    assert "Testbetreff" in messages[0]["content"]
    assert "Hallo, bitte antworte kurz." in messages[0]["content"]
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Verstanden, ich kümmere mich darum."


async def test_process_inbound_emails_does_nothing_when_inbox_is_empty(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    await _connect_smtp_and_imap(client, auth_headers)

    async def fake_fetch_unseen_emails(db, user):  # noqa: ARG001
        return []

    monkeypatch.setattr(email_service, "fetch_unseen_emails", fake_fetch_unseen_emails)

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        processed = await email_inbox_service.process_inbound_emails(db, user)

    assert processed == 0

    async with async_session_maker() as db:
        conversations = (await db.execute(select(Conversation))).scalars().all()
        assert conversations == []


async def test_users_with_inbound_agent_enabled_only_lists_opted_in_users(
    client: AsyncClient, auth_headers: dict
):
    await _connect_smtp_and_imap(client, auth_headers)

    async with async_session_maker() as db:
        none_enabled = await email_inbox_service.users_with_inbound_agent_enabled(db)
        assert none_enabled == []

    await client.patch("/integrations/email/inbound-agent", json={"enabled": True}, headers=auth_headers)

    async with async_session_maker() as db:
        enabled = await email_inbox_service.users_with_inbound_agent_enabled(db)
        assert len(enabled) == 1


async def test_scheduler_check_inbound_email_processes_opted_in_users(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    await _connect_smtp_and_imap(client, auth_headers)
    await client.patch("/integrations/email/inbound-agent", json={"enabled": True}, headers=auth_headers)

    async def fake_fetch_unseen_emails(db, user):  # noqa: ARG001
        return [{"from": "a@example.com", "subject": "Via Scheduler", "body": "Hi"}]

    monkeypatch.setattr(email_service, "fetch_unseen_emails", fake_fetch_unseen_emails)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Ok.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await scheduler._check_inbound_email()

    listed = await client.get("/chat/conversations", headers=auth_headers)
    assert listed.json()["conversations"][0]["title"] == "E-Mail: Via Scheduler"


async def test_scheduler_check_inbound_email_skips_users_without_it_enabled(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    await _connect_smtp_and_imap(client, auth_headers)  # connected, but never enabled

    async def fake_fetch_unseen_emails(db, user):  # noqa: ARG001
        raise AssertionError("must not be called for a user who hasn't enabled inbound_agent")

    monkeypatch.setattr(email_service, "fetch_unseen_emails", fake_fetch_unseen_emails)

    await scheduler._check_inbound_email()

    listed = await client.get("/chat/conversations", headers=auth_headers)
    assert listed.json()["conversations"] == []

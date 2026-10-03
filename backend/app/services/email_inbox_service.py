from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.db.models import Conversation, EmailAccount, User
from app.services import email_service, log_service
from app.services.ollama_client import OllamaError

MAX_SUBJECT_IN_TITLE = 240


def _conversation_title(subject: str) -> str:
    return f"E-Mail: {subject}"[:MAX_SUBJECT_IN_TITLE]


def _format_email_as_message(email: dict) -> str:
    return f"Von: {email['from']}\nBetreff: {email['subject']}\n\n{email['body']}"


async def users_with_inbound_agent_enabled(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).join(EmailAccount).where(EmailAccount.inbound_agent_enabled.is_(True)))
    return list(result.scalars().all())


async def process_inbound_emails(db: AsyncSession, user: User) -> int:
    """Fetches every unseen email for `user` (see email_service.fetch_unseen_emails) and runs
    each one through the normal chat agent loop (app.agent.orchestrator.run_turn), each in its
    own new Conversation with skill="email_inbox" (see app/agent/skills.py for the
    untrusted-content framing and full tool access - the user explicitly chose full autonomy
    over a restricted preset or a confirm-first flow for this feature). Reuses the exact same,
    already-tested turn logic a normal chat message goes through, so the result is a real
    conversation the user can review/continue in the Chat UI, not a separate parallel log.
    Returns how many emails were found (processed or not, if one failed - see below).
    """
    emails = await email_service.fetch_unseen_emails(db, user)
    for incoming in emails:
        conversation = Conversation(
            user_id=user.id, title=_conversation_title(incoming["subject"]), skill="email_inbox"
        )
        db.add(conversation)
        await db.flush()
        try:
            await run_turn(db, user, conversation, _format_email_as_message(incoming))
        except OllamaError as exc:
            await log_service.log(
                db,
                category="email_inbox",
                level="error",
                user=user,
                message=f'Verarbeitung einer eingehenden E-Mail fehlgeschlagen (Betreff: "{incoming["subject"]}").',
                detail=str(exc),
            )
    return len(emails)

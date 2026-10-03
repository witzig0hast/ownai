from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, PendingAction, User
from app.errors import APIError, NotFound


class PendingActionAlreadyResolved(APIError):
    def __init__(self, message: str = "Diese Aktion wurde bereits entschieden."):
        super().__init__(409, "pending_action_already_resolved", message)


async def list_pending(db: AsyncSession, user: User) -> list[PendingAction]:
    result = await db.execute(
        select(PendingAction)
        .where(PendingAction.user_id == user.id, PendingAction.status == "pending")
        .order_by(PendingAction.created_at)
    )
    return list(result.scalars().all())


async def _get_owned_pending(db: AsyncSession, user: User, pending_id: str) -> PendingAction:
    action = await db.get(PendingAction, pending_id)
    if action is None or action.user_id != user.id:
        raise NotFound("Ausstehende Aktion nicht gefunden.")
    if action.status != "pending":
        raise PendingActionAlreadyResolved()
    return action


async def approve(db: AsyncSession, user: User, pending_id: str) -> PendingAction:
    """Actually executes the queued tool call (bypassing the approval gate itself, obviously -
    see app/agent/tool_execution.py for where this was first queued instead of run) and appends
    a short note to the conversation it came from, so the resolution is visible right there
    alongside the agent's original proposal, not just in this list."""
    from app.agent.tools import TOOL_HANDLERS  # lazy: tools.py imports this module too

    action = await _get_owned_pending(db, user, pending_id)
    conversation = await db.get(Conversation, action.conversation_id)

    handler = TOOL_HANDLERS.get(action.tool_name)
    try:
        result = await handler(db, user, conversation, action.arguments) if handler else {"error": "Unbekanntes Werkzeug."}
    except APIError as exc:
        result = {"error": exc.message}
    except Exception as exc:  # noqa: BLE001 - a failed action must still resolve the approval cleanly
        result = {"error": str(exc)}

    action.status = "approved"
    action.resolved_at = datetime.now(timezone.utc)

    if conversation is not None:
        note = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"✓ Bestätigt und ausgeführt: {action.summary}",
            tool_calls=[{"tool": action.tool_name, "arguments": action.arguments, "result": result}],
        )
        db.add(note)

    await db.commit()
    await db.refresh(action)
    return action


async def decline(db: AsyncSession, user: User, pending_id: str) -> PendingAction:
    action = await _get_owned_pending(db, user, pending_id)
    conversation = await db.get(Conversation, action.conversation_id)

    action.status = "declined"
    action.resolved_at = datetime.now(timezone.utc)

    if conversation is not None:
        note = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"✗ Abgelehnt: {action.summary}",
        )
        db.add(note)

    await db.commit()
    await db.refresh(action)
    return action

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import generate_agent_api_key
from app.db.models import AgentIdentity, AgentMessage, User
from app.errors import APIError, AgentNameTaken, AgentNotFound
from app.services import push_service

# Reserved `to`/`from` name meaning "the account owner / OwnAI itself" - not a row in
# agent_identities, since it doesn't need its own API key (the user is already authenticated).
OWNAI_LABEL = "ownai"


async def register_agent(
    db: AsyncSession, user: User, *, name: str, description: str | None
) -> tuple[AgentIdentity, str]:
    if name.lower() == OWNAI_LABEL:
        raise AgentNameTaken(f"'{OWNAI_LABEL}' ist reserviert und kann nicht als Agent-Name verwendet werden.")

    existing = await db.execute(
        select(AgentIdentity).where(AgentIdentity.user_id == user.id, AgentIdentity.name == name)
    )
    if existing.scalar_one_or_none() is not None:
        raise AgentNameTaken()

    raw_key, key_hash = generate_agent_api_key()
    agent = AgentIdentity(user_id=user.id, name=name, description=description, api_key_hash=key_hash)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent, raw_key


async def list_agents(db: AsyncSession, user: User) -> list[AgentIdentity]:
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.user_id == user.id).order_by(AgentIdentity.created_at)
    )
    return list(result.scalars().all())


async def get_owned_agent(db: AsyncSession, user: User, agent_id: str) -> AgentIdentity:
    agent = await db.get(AgentIdentity, agent_id)
    if agent is None or agent.user_id != user.id:
        raise AgentNotFound()
    return agent


async def delete_agent(db: AsyncSession, user: User, agent_id: str) -> None:
    agent = await get_owned_agent(db, user, agent_id)
    await db.delete(agent)
    await db.commit()


async def _resolve_target(db: AsyncSession, user: User, to_name: str) -> tuple[AgentIdentity | None, str]:
    if to_name.lower() == OWNAI_LABEL:
        return None, OWNAI_LABEL
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.user_id == user.id, AgentIdentity.name == to_name)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound(f"Agent '{to_name}' ist nicht registriert.")
    return agent, agent.name


async def send_message(
    db: AsyncSession,
    user: User,
    *,
    from_agent: AgentIdentity | None,
    to_name: str,
    kind: str,
    content: str | None = None,
    task_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AgentMessage:
    to_agent, to_label = await _resolve_target(db, user, to_name)
    from_label = from_agent.name if from_agent is not None else OWNAI_LABEL

    message = AgentMessage(
        user_id=user.id,
        from_agent_id=from_agent.id if from_agent is not None else None,
        from_label=from_label,
        to_agent_id=to_agent.id if to_agent is not None else None,
        to_label=to_label,
        kind=kind,
        content=content,
        task_type=task_type,
        payload=payload,
        status="pending" if kind == "task" else "sent",
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    if to_agent is None:
        # Addressed to the account owner - this is a proactive-contact channel too: a message
        # sent by another one of the user's own projects onto the bus reaches them without
        # OwnAI having to be asked first.
        summary = content if kind == "text" else f"Task '{task_type}' von {from_label}"
        try:
            await push_service.send_push(
                db, user, title=f"Agent Bus: Nachricht von {from_label}", body=(summary or "")[:200]
            )
        except Exception:  # noqa: BLE001 - a failed push must never fail the already-saved message
            pass

    return message


async def list_messages(
    db: AsyncSession, user: User, *, agent_id: str | None = None, status: str | None = None
) -> list[AgentMessage]:
    query = select(AgentMessage).where(AgentMessage.user_id == user.id)
    if agent_id:
        query = query.where(
            (AgentMessage.from_agent_id == agent_id) | (AgentMessage.to_agent_id == agent_id)
        )
    if status:
        query = query.where(AgentMessage.status == status)
    result = await db.execute(query.order_by(AgentMessage.created_at.desc()))
    return list(result.scalars().all())


async def list_inbox(db: AsyncSession, agent: AgentIdentity) -> list[AgentMessage]:
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.user_id == agent.user_id, AgentMessage.to_agent_id == agent.id)
        .order_by(AgentMessage.created_at.desc())
    )
    return list(result.scalars().all())


async def submit_result(
    db: AsyncSession, agent: AgentIdentity, message_id: str, *, status: str, result: dict[str, Any] | None
) -> AgentMessage:
    message = await db.get(AgentMessage, message_id)
    if message is None or message.to_agent_id != agent.id:
        raise AgentNotFound("Nachricht nicht gefunden oder nicht an diesen Agent adressiert.")
    if message.kind != "task":
        raise APIError(422, "not_a_task", "Nur Task-Nachrichten können ein Ergebnis melden.")

    message.status = status
    message.result = result
    await db.commit()
    await db.refresh(message)
    return message

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_agent_by_api_key, get_current_user
from app.auth.security import hash_agent_api_key
from app.db.models import AgentIdentity, User
from app.db.session import get_db
from app.errors import InvalidAgentKey, NotAuthenticated
from app.schemas.agent_bus import (
    AgentIdentitiesListOut,
    AgentIdentityCreateRequest,
    AgentIdentityCreateResponse,
    AgentMessageOut,
    AgentMessageResultRequest,
    AgentMessageSendRequest,
    AgentMessagesListOut,
)
from app.services import agent_bus_service

router = APIRouter(prefix="/agent-bus", tags=["agent-bus"])


async def _resolve_sender(
    x_agent_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, AgentIdentity | None]:
    """POST /agent-bus/messages is sent either by the account owner (Bearer, e.g. from the web
    UI or the chat tool) or by one of their registered external agents (X-Agent-Key) - this
    resolves either into (user, from_agent), with from_agent=None meaning "OwnAI/the user"."""
    if x_agent_key:
        key_hash = hash_agent_api_key(x_agent_key)
        result = await db.execute(select(AgentIdentity).where(AgentIdentity.api_key_hash == key_hash))
        agent = result.scalar_one_or_none()
        if agent is None:
            raise InvalidAgentKey()
        user = await db.get(User, agent.user_id)
        if user is None:
            raise InvalidAgentKey()
        return user, agent

    if authorization and authorization.lower().startswith("bearer "):
        user = await get_current_user(authorization=authorization, db=db)
        return user, None

    raise NotAuthenticated("Weder X-Agent-Key noch Authorization-Header gesetzt.")


@router.post("/agents", response_model=AgentIdentityCreateResponse, status_code=201)
async def register_agent(
    payload: AgentIdentityCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentIdentityCreateResponse:
    agent, raw_key = await agent_bus_service.register_agent(
        db, user, name=payload.name, description=payload.description
    )
    return AgentIdentityCreateResponse(
        id=agent.id, name=agent.name, description=agent.description, created_at=agent.created_at, api_key=raw_key
    )


@router.get("/agents", response_model=AgentIdentitiesListOut)
async def list_agents(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentIdentitiesListOut:
    agents = await agent_bus_service.list_agents(db, user)
    return AgentIdentitiesListOut(agents=agents)


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await agent_bus_service.delete_agent(db, user, agent_id)


@router.post("/messages", response_model=AgentMessageOut, status_code=201)
async def send_message(
    payload: AgentMessageSendRequest,
    sender: tuple[User, AgentIdentity | None] = Depends(_resolve_sender),
    db: AsyncSession = Depends(get_db),
) -> AgentMessageOut:
    user, from_agent = sender
    return await agent_bus_service.send_message(
        db,
        user,
        from_agent=from_agent,
        to_name=payload.to,
        kind=payload.kind,
        content=payload.content,
        task_type=payload.task_type,
        payload=payload.payload,
    )


@router.get("/messages", response_model=AgentMessagesListOut)
async def list_messages(
    agent_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentMessagesListOut:
    messages = await agent_bus_service.list_messages(db, user, agent_id=agent_id, status=status)
    return AgentMessagesListOut(messages=messages)


@router.get("/inbox", response_model=AgentMessagesListOut)
async def get_inbox(
    agent: AgentIdentity = Depends(get_agent_by_api_key), db: AsyncSession = Depends(get_db)
) -> AgentMessagesListOut:
    messages = await agent_bus_service.list_inbox(db, agent)
    return AgentMessagesListOut(messages=messages)


@router.post("/messages/{message_id}/result", response_model=AgentMessageOut)
async def submit_result(
    message_id: str,
    payload: AgentMessageResultRequest,
    agent: AgentIdentity = Depends(get_agent_by_api_key),
    db: AsyncSession = Depends(get_db),
) -> AgentMessageOut:
    return await agent_bus_service.submit_result(
        db, agent, message_id, status=payload.status, result=payload.result
    )

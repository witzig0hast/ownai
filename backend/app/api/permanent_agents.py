from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent_presets import PRESETS
from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.permanent_agent import (
    AgentLogEntriesListOut,
    AgentPresetOut,
    AgentPresetsListOut,
    PermanentAgentCreateRequest,
    PermanentAgentOut,
    PermanentAgentsListOut,
    PermanentAgentUpdateRequest,
)
from app.services import permanent_agent_service

router = APIRouter(prefix="/permanent-agents", tags=["permanent-agents"])


@router.get("/presets", response_model=AgentPresetsListOut)
async def list_presets(_user: User = Depends(get_current_user)) -> AgentPresetsListOut:
    return AgentPresetsListOut(
        presets=[AgentPresetOut(key=p.key, name=p.name, description=p.description) for p in PRESETS.values()]
    )


@router.post("", response_model=PermanentAgentOut, status_code=201)
async def create_agent(
    payload: PermanentAgentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PermanentAgentOut:
    return await permanent_agent_service.add_agent(db, user, payload)


@router.get("", response_model=PermanentAgentsListOut)
async def list_agents(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PermanentAgentsListOut:
    agents = await permanent_agent_service.list_agents(db, user)
    return PermanentAgentsListOut(agents=agents)


@router.patch("/{agent_id}", response_model=PermanentAgentOut)
async def update_agent(
    agent_id: str,
    payload: PermanentAgentUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PermanentAgentOut:
    return await permanent_agent_service.update_agent(db, user, agent_id, payload)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await permanent_agent_service.delete_agent(db, user, agent_id)


@router.get("/{agent_id}/log", response_model=AgentLogEntriesListOut)
async def list_log_entries(
    agent_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentLogEntriesListOut:
    entries = await permanent_agent_service.list_log_entries(db, user, agent_id, limit)
    return AgentLogEntriesListOut(entries=entries)

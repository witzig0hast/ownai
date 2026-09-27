from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.home_assistant import (
    HomeAssistantConnectRequest,
    HomeAssistantConnectResponse,
    HomeAssistantEntitiesListOut,
)
from app.services import home_assistant_service

router = APIRouter(tags=["home-assistant"])


@router.post("/integrations/home-assistant", response_model=HomeAssistantConnectResponse)
async def connect_home_assistant(
    payload: HomeAssistantConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeAssistantConnectResponse:
    await home_assistant_service.connect(db, user, payload.url, payload.token)
    return HomeAssistantConnectResponse()


@router.get("/home-assistant/entities", response_model=HomeAssistantEntitiesListOut)
async def list_home_assistant_entities(
    domain: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeAssistantEntitiesListOut:
    entities = await home_assistant_service.list_entities(db, user, domain)
    return HomeAssistantEntitiesListOut(entities=entities)

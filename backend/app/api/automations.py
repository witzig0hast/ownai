from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.automation import (
    AutomationCreateRequest,
    AutomationOut,
    AutomationsListOut,
    AutomationUpdateRequest,
)
from app.services import automation_service

router = APIRouter(prefix="/automations", tags=["automations"])


@router.post("", response_model=AutomationOut, status_code=201)
async def create_automation(
    payload: AutomationCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationOut:
    return await automation_service.add_automation(db, user, payload)


@router.get("", response_model=AutomationsListOut)
async def list_automations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AutomationsListOut:
    automations = await automation_service.list_automations(db, user)
    return AutomationsListOut(automations=automations)


@router.patch("/{automation_id}", response_model=AutomationOut)
async def update_automation(
    automation_id: str,
    payload: AutomationUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationOut:
    return await automation_service.update_automation(db, user, automation_id, payload)


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await automation_service.delete_automation(db, user, automation_id)

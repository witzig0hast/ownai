from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.services import onboarding_service
from app.services.onboarding_service import SetupItem

router = APIRouter(prefix="/users/me/setup-status", tags=["onboarding"])


class SetupStatusOut(BaseModel):
    items: list[SetupItem]
    completed: int
    total: int
    dismissed: bool


class SetupStatusUpdate(BaseModel):
    dismissed: bool


async def _status(db: AsyncSession, user: User) -> SetupStatusOut:
    items = await onboarding_service.setup_items(db, user)
    return SetupStatusOut(
        items=items,
        completed=sum(1 for i in items if i.done),
        total=len(items),
        dismissed=user.onboarding_dismissed,
    )


@router.get("", response_model=SetupStatusOut)
async def get_setup_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> SetupStatusOut:
    return await _status(db, user)


@router.put("", response_model=SetupStatusOut)
async def update_setup_status(
    payload: SetupStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SetupStatusOut:
    user.onboarding_dismissed = payload.dismissed
    await db.commit()
    await db.refresh(user)
    return await _status(db, user)

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.services import overview_service

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("")
async def get_overview(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await overview_service.build(db, user)


@router.get("/briefing")
async def get_briefing(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    overview = await overview_service.build(db, user)
    return {"text": overview_service.briefing_text(overview)}

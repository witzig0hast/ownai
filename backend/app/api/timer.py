from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.timer import TimerOut, TimersListOut
from app.services import timer_service

router = APIRouter(tags=["timers"])


@router.get("/timers", response_model=TimersListOut)
async def list_timers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimersListOut:
    timers = await timer_service.list_active_timers(db, user)
    return TimersListOut(timers=[TimerOut(id=t.id, label=t.label, ends_at=t.ends_at) for t in timers])


@router.post("/timers/{timer_id}/cancel", response_model=TimerOut)
async def cancel_timer(
    timer_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimerOut:
    timer = await timer_service.cancel_timer(db, user, timer_id)
    return TimerOut(id=timer.id, label=timer.label, ends_at=timer.ends_at)

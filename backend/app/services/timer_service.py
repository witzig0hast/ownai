from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Timer, User
from app.errors import APIError

MAX_DURATION_SECONDS = 24 * 60 * 60  # a day - generous upper bound against a bad/huge LLM argument


class TimerNotFound(APIError):
    def __init__(self, message: str = "Timer nicht gefunden."):
        super().__init__(404, "timer_not_found", message)


class InvalidTimerDuration(APIError):
    def __init__(self, message: str):
        super().__init__(422, "invalid_timer_duration", message)


async def create_timer(db: AsyncSession, user: User, duration_seconds: int, label: str | None) -> Timer:
    if duration_seconds <= 0 or duration_seconds > MAX_DURATION_SECONDS:
        raise InvalidTimerDuration(
            f"duration_seconds muss zwischen 1 und {MAX_DURATION_SECONDS} liegen, war {duration_seconds}."
        )
    timer = Timer(
        user_id=user.id,
        label=label,
        ends_at=datetime.now(timezone.utc) + timedelta(seconds=duration_seconds),
    )
    db.add(timer)
    await db.commit()
    await db.refresh(timer)
    return timer


async def list_active_timers(db: AsyncSession, user: User) -> list[Timer]:
    """Non-cancelled timers, including already-expired ones (clients decide what "expired" means
    for their purposes - e.g. a web tab still open shows a firing alert, one reopened later shows
    "already abgelaufen um HH:MM")."""
    result = await db.execute(
        select(Timer).where(Timer.user_id == user.id, Timer.cancelled.is_(False)).order_by(Timer.ends_at)
    )
    return list(result.scalars().all())


async def cancel_timer(db: AsyncSession, user: User, timer_id: str) -> Timer:
    result = await db.execute(select(Timer).where(Timer.id == timer_id, Timer.user_id == user.id))
    timer = result.scalar_one_or_none()
    if timer is None:
        raise TimerNotFound()
    timer.cancelled = True
    await db.commit()
    await db.refresh(timer)
    return timer

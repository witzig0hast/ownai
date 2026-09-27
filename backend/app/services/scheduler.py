import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.models import Timer, User
from app.db.session import async_session_maker
from app.services import push_service

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _check_expired_timers() -> None:
    """Polls for timers that expired since the last check and pushes a proactive notification
    for each - the one place in the app where the assistant contacts the user unprompted rather
    than reacting to a request. `Timer.notified` ensures each expiry is only ever pushed once."""
    now = datetime.now(timezone.utc)
    async with async_session_maker() as db:
        result = await db.execute(
            select(Timer).where(Timer.cancelled.is_(False), Timer.notified.is_(False), Timer.ends_at <= now)
        )
        expired = list(result.scalars().all())
        if not expired:
            return

        for timer in expired:
            timer.notified = True
            user = await db.get(User, timer.user_id)
            if user is None:
                continue
            try:
                await push_service.send_push(db, user, title="Timer abgelaufen", body=timer.label or "Timer")
            except Exception:  # noqa: BLE001 - one failed push must not block the others or the loop
                logger.exception("Failed to send push for expired timer %s", timer.id)
        await db.commit()


def start_scheduler() -> AsyncIOScheduler:
    """Starts the background poll for expired timers (see _check_expired_timers). Runs
    in-process via APScheduler. Known limitation: with multiple worker processes, each would
    poll independently and could send duplicate notifications - docker-compose.yml runs a
    single uvicorn process, so this doesn't apply today, but is worth knowing before scaling out
    to multiple workers/replicas (would need a DB-level lock or moving this to a dedicated
    worker process)."""
    global _scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_check_expired_timers, "interval", seconds=15, id="expired_timers")
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

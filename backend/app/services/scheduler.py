import logging
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.models import Timer, User
from app.db.session import async_session_maker
from app.services import contact_service, push_service, reminder_service

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


async def _check_birthdays() -> None:
    """Runs once a day (see start_scheduler) and pushes a proactive notification for every
    contact whose birthday is today - the third proactive channel alongside expired timers and
    Agent Bus messages. `Contact.last_birthday_push_date` (set to today's ISO date after a push)
    guards against sending twice if the job somehow runs more than once on the same day (e.g. a
    restart). Runs in server time - there's no per-user timezone stored yet, so "today" is the
    scheduler process's local date."""
    today = date.today()
    async with async_session_maker() as db:
        contacts = await contact_service.contacts_with_birthday_on(db, today)
        if not contacts:
            return

        for contact in contacts:
            user = await db.get(User, contact.user_id)
            if user is None:
                continue
            contact.last_birthday_push_date = today.isoformat()
            body = contact.name
            if contact.birthday_year is not None:
                body = f"{contact.name} wird heute {today.year - contact.birthday_year}"
            try:
                await push_service.send_push(db, user, title="Geburtstag", body=body)
            except Exception:  # noqa: BLE001 - one failed push must not block the others or the loop
                logger.exception("Failed to send birthday push for contact %s", contact.id)
        await db.commit()


async def _check_recurring_reminders() -> None:
    """Runs once a minute (see start_scheduler) and pushes a proactive notification for every
    active RecurringReminder whose recurrence/hour/minute matches now - a repeatable counterpart
    to Timer's one-off countdown. Matched against local server time (like _check_birthdays; no
    per-user timezone stored yet). `RecurringReminder.last_triggered_date` guards against firing
    twice within the same minute-resolution poll on the same day."""
    now = datetime.now()
    async with async_session_maker() as db:
        due = await reminder_service.reminders_due_at(db, now)
        if not due:
            return

        for reminder in due:
            user = await db.get(User, reminder.user_id)
            if user is None:
                continue
            reminder.last_triggered_date = now.date().isoformat()
            try:
                await push_service.send_push(db, user, title="Erinnerung", body=reminder.label)
            except Exception:  # noqa: BLE001 - one failed push must not block the others or the loop
                logger.exception("Failed to send push for recurring reminder %s", reminder.id)
        await db.commit()


def start_scheduler() -> AsyncIOScheduler:
    """Starts the background poll for expired timers (see _check_expired_timers), the daily
    birthday check (see _check_birthdays), and the per-minute recurring-reminder check (see
    _check_recurring_reminders). Runs in-process via APScheduler. Known limitation: with multiple
    worker processes, each would poll independently and could send duplicate notifications -
    docker-compose.yml runs a single uvicorn process, so this doesn't apply today, but is worth
    knowing before scaling out to multiple workers/replicas (would need a DB-level lock or moving
    this to a dedicated worker process)."""
    global _scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_check_expired_timers, "interval", seconds=15, id="expired_timers")
    scheduler.add_job(_check_birthdays, "cron", hour=8, minute=0, id="birthdays")
    scheduler.add_job(_check_recurring_reminders, "cron", second=0, id="recurring_reminders")
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

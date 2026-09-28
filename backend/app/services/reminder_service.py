from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RecurringReminder, User
from app.errors import NotFound
from app.schemas.reminder import ReminderCreateRequest, ReminderUpdateRequest

_WEEKDAY_BY_INDEX = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


async def add_reminder(db: AsyncSession, user: User, payload: ReminderCreateRequest) -> RecurringReminder:
    reminder = RecurringReminder(
        user_id=user.id,
        label=payload.label.strip(),
        recurrence=payload.recurrence,
        hour=payload.hour,
        minute=payload.minute,
        weekday=payload.weekday,
        day_of_month=payload.day_of_month,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def list_reminders(db: AsyncSession, user: User) -> list[RecurringReminder]:
    result = await db.execute(
        select(RecurringReminder)
        .where(RecurringReminder.user_id == user.id)
        .order_by(RecurringReminder.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_owned_reminder(db: AsyncSession, user: User, reminder_id: str) -> RecurringReminder:
    reminder = await db.get(RecurringReminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise NotFound("Erinnerung nicht gefunden.")
    return reminder


async def update_reminder(
    db: AsyncSession, user: User, reminder_id: str, payload: ReminderUpdateRequest
) -> RecurringReminder:
    reminder = await _get_owned_reminder(db, user, reminder_id)
    if payload.label is not None:
        reminder.label = payload.label.strip()
    if payload.recurrence is not None:
        reminder.recurrence = payload.recurrence
    if payload.hour is not None:
        reminder.hour = payload.hour
    if payload.minute is not None:
        reminder.minute = payload.minute
    if payload.weekday is not None:
        reminder.weekday = payload.weekday
    if payload.day_of_month is not None:
        reminder.day_of_month = payload.day_of_month
    if payload.active is not None:
        reminder.active = payload.active
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def delete_reminder(db: AsyncSession, user: User, reminder_id: str) -> None:
    reminder = await _get_owned_reminder(db, user, reminder_id)
    await db.delete(reminder)
    await db.commit()


async def reminders_due_at(db: AsyncSession, now: datetime) -> list[RecurringReminder]:
    """Active reminders whose recurrence matches `now`'s weekday/day-of-month, hour and minute, and
    that haven't already fired today - used by the scheduler's minute-resolution poll
    (app/services/scheduler.py)."""
    today_iso = now.date().isoformat()
    result = await db.execute(
        select(RecurringReminder).where(
            RecurringReminder.active.is_(True),
            RecurringReminder.hour == now.hour,
            RecurringReminder.minute == now.minute,
        )
    )
    due = []
    for reminder in result.scalars().all():
        if reminder.last_triggered_date == today_iso:
            continue
        if reminder.recurrence == "weekly" and reminder.weekday != _WEEKDAY_BY_INDEX[now.weekday()]:
            continue
        if reminder.recurrence == "monthly" and reminder.day_of_month != now.day:
            continue
        due.append(reminder)
    return due

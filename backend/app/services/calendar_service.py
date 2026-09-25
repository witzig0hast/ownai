import asyncio
import uuid
from datetime import datetime, timezone

import caldav
from icalendar import Calendar as ICalendar
from icalendar import Event as ICalEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CalendarAccount, User
from app.errors import CalendarNotConnected
from app.services.crypto import decrypt, encrypt


async def get_account(db: AsyncSession, user: User) -> CalendarAccount | None:
    result = await db.execute(select(CalendarAccount).where(CalendarAccount.user_id == user.id))
    return result.scalar_one_or_none()


async def connect(db: AsyncSession, user: User, url: str, username: str, password: str) -> CalendarAccount:
    existing = await get_account(db, user)
    if existing is not None:
        existing.url = url
        existing.username = username
        existing.encrypted_password = encrypt(password)
        account = existing
    else:
        account = CalendarAccount(
            user_id=user.id,
            url=url,
            username=username,
            encrypted_password=encrypt(password),
        )
        db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


def _default_calendar(account: CalendarAccount) -> caldav.Calendar:
    """Blocking: opens a DAVClient and returns the principal's first calendar. Run via asyncio.to_thread."""
    client = caldav.DAVClient(
        url=account.url,
        username=account.username,
        password=decrypt(account.encrypted_password),
    )
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise CalendarNotConnected("Der CalDAV-Account hat keinen erreichbaren Kalender.")
    return calendars[0]


def _event_component_to_dict(component) -> dict:
    dtstart = component.get("dtstart").dt
    dtend = component.get("dtend").dt if component.get("dtend") else dtstart
    if not isinstance(dtstart, datetime):
        dtstart = datetime(dtstart.year, dtstart.month, dtstart.day, tzinfo=timezone.utc)
    if not isinstance(dtend, datetime):
        dtend = datetime(dtend.year, dtend.month, dtend.day, tzinfo=timezone.utc)
    location = component.get("location")
    return {
        "id": str(component.get("uid")),
        "title": str(component.get("summary") or ""),
        "start": dtstart,
        "end": dtend,
        "location": str(location) if location else None,
        "source": "caldav",
    }


def _list_events_blocking(account: CalendarAccount, start: datetime, end: datetime) -> list[dict]:
    calendar = _default_calendar(account)
    results = calendar.date_search(start=start, end=end)
    events = []
    for event in results:
        try:
            events.append(_event_component_to_dict(event.icalendar_component))
        except Exception:  # noqa: BLE001 - a single malformed remote event must not break the whole list
            continue
    return events


def _create_event_blocking(
    account: CalendarAccount, title: str, start: datetime, end: datetime, location: str | None
) -> dict:
    calendar = _default_calendar(account)

    ical = ICalendar()
    ical.add("prodid", "-//OwnAI//ownai.local//")
    ical.add("version", "2.0")

    component = ICalEvent()
    component.add("summary", title)
    component.add("dtstart", start)
    component.add("dtend", end)
    if location:
        component.add("location", location)
    event_uid = f"{uuid.uuid4()}@ownai"
    component.add("uid", event_uid)
    component.add("dtstamp", datetime.now(timezone.utc))
    ical.add_component(component)

    calendar.save_event(ical=ical.to_ical().decode("utf-8"))

    return {
        "id": event_uid,
        "title": title,
        "start": start,
        "end": end,
        "location": location,
        "source": "caldav",
    }


async def list_events(db: AsyncSession, user: User, start: datetime, end: datetime) -> list[dict]:
    account = await get_account(db, user)
    if account is None:
        raise CalendarNotConnected()
    return await asyncio.to_thread(_list_events_blocking, account, start, end)


async def create_event(
    db: AsyncSession, user: User, title: str, start: datetime, end: datetime, location: str | None
) -> dict:
    account = await get_account(db, user)
    if account is None:
        raise CalendarNotConnected()
    return await asyncio.to_thread(_create_event_blocking, account, title, start, end, location)

"""Everything the "Übersicht" start page and the morning briefing show, in one call: today's
events, open list items, the next reminders, upcoming birthdays, this month's spending, the
weather for the user's home city and how many confirmations are waiting.

Each section is computed independently and degrades on its own: an unreachable CalDAV server or
weather service turns into that section's `error`, never into a failed page. Network sections
run in parallel with a timeout, so one slow dependency can't stall the whole start page."""

import asyncio
import calendar as calendar_module
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contact, PendingAction, RecurringReminder, User
from app.errors import APIError
from app.services import calendar_service, expense_service, list_service, weather_service
from app.utils import local_now, local_tz

NETWORK_TIMEOUT_SECONDS = 6.0
BIRTHDAY_LOOKAHEAD_DAYS = 30
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def next_reminder_occurrence(reminder: RecurringReminder, now: datetime) -> datetime | None:
    """Next wall-clock time (in now's zone) this reminder fires, at or after `now`."""
    for offset in range(0, 62):
        day = (now + timedelta(days=offset)).date()
        if reminder.recurrence == "weekly" and reminder.weekday != _WEEKDAYS[day.weekday()]:
            continue
        if reminder.recurrence == "monthly" and reminder.day_of_month != day.day:
            continue
        candidate = datetime.combine(day, time(reminder.hour, reminder.minute), tzinfo=now.tzinfo)
        if candidate >= now.replace(second=0, microsecond=0):
            return candidate
    return None


def next_birthday(contact: Contact, today: date) -> date | None:
    if contact.birthday_month is None or contact.birthday_day is None:
        return None
    for year in (today.year, today.year + 1):
        day = contact.birthday_day
        # 29 February in a non-leap year is celebrated on the 28th.
        if contact.birthday_month == 2 and day == 29 and not calendar_module.isleap(year):
            day = 28
        candidate = date(year, contact.birthday_month, day)
        if candidate >= today:
            return candidate
    return None


async def _with_timeout(coro) -> tuple[Any, str | None]:
    try:
        return await asyncio.wait_for(coro, timeout=NETWORK_TIMEOUT_SECONDS), None
    except TimeoutError:
        return None, "Zeitüberschreitung - der Dienst antwortet gerade nicht."
    except APIError as exc:
        return None, exc.message
    except Exception as exc:  # noqa: BLE001 - one broken section must not take the page down
        return None, str(exc) or exc.__class__.__name__


async def build(db: AsyncSession, user: User) -> dict[str, Any]:
    now = local_now()
    today = now.date()

    # --- DB sections, sequentially (an AsyncSession is not safe for concurrent use) ---
    lists = await list_service.list_lists(db, user)
    lists_out = [
        {
            "id": lst.id,
            "name": lst.name,
            "kind": lst.kind,
            "open_count": sum(1 for i in lst.items if not i.done),
            "open_items": [{"id": i.id, "content": i.content} for i in lst.items if not i.done][:6],
        }
        for lst in lists
    ]

    reminder_rows = (
        await db.execute(
            select(RecurringReminder).where(RecurringReminder.user_id == user.id, RecurringReminder.active.is_(True))
        )
    ).scalars()
    upcoming_reminders = []
    for reminder in reminder_rows:
        next_at = next_reminder_occurrence(reminder, now)
        if next_at is not None:
            upcoming_reminders.append({"id": reminder.id, "label": reminder.label, "next_at": next_at.isoformat()})
    upcoming_reminders.sort(key=lambda r: r["next_at"])

    contacts = (await db.execute(select(Contact).where(Contact.user_id == user.id))).scalars()
    birthdays = []
    for contact in contacts:
        when = next_birthday(contact, today)
        if when is None or (when - today).days > BIRTHDAY_LOOKAHEAD_DAYS:
            continue
        birthdays.append(
            {
                "contact_id": contact.id,
                "name": contact.name,
                "date": when.isoformat(),
                "days_until": (when - today).days,
                "turns": when.year - contact.birthday_year if contact.birthday_year else None,
            }
        )
    birthdays.sort(key=lambda b: b["days_until"])

    month_start = today.replace(day=1)
    month_expenses = await expense_service.list_expenses(db, user, date_from=month_start, date_to=today)
    month_total, by_category = expense_service.totals(month_expenses)

    pending_count = await db.scalar(
        select(func.count()).select_from(PendingAction).where(
            PendingAction.user_id == user.id, PendingAction.status == "pending"
        )
    )

    calendar_account = await calendar_service.get_account(db, user)

    # --- Network sections, in parallel ---
    day_start = datetime.combine(today, time.min, tzinfo=local_tz())
    day_end = datetime.combine(today, time.max, tzinfo=local_tz())

    async def fetch_events():
        events = await asyncio.to_thread(calendar_service._list_events_blocking, calendar_account, day_start, day_end)
        events.sort(key=lambda e: e["start"])
        return [
            {
                "title": e["title"],
                "start": e["start"].isoformat(),
                "end": e["end"].isoformat(),
                "location": e["location"],
                # CalDAV all-day events come back as midnight-to-midnight (see calendar_service).
                "all_day": (e["end"] - e["start"]) >= timedelta(hours=23),
            }
            for e in events
        ]

    async def nothing():
        return None

    (events, events_error), (weather, weather_error) = await asyncio.gather(
        _with_timeout(fetch_events()) if calendar_account else _with_timeout(nothing()),
        _with_timeout(weather_service.weather_for_location(user.home_city)) if user.home_city else _with_timeout(nothing()),
    )

    return {
        "display_name": user.display_name,
        "today": today.isoformat(),
        "calendar": {
            "connected": calendar_account is not None,
            "events": events or [],
            "error": events_error,
        },
        "lists": [lst for lst in lists_out if lst["open_count"] > 0] + [lst for lst in lists_out if lst["open_count"] == 0],
        "reminders": upcoming_reminders[:5],
        "birthdays": birthdays[:5],
        "expenses": {
            "month_total": round(month_total, 2),
            "count": len(month_expenses),
            "by_category": sorted(
                ({"category": k, "total": round(v, 2)} for k, v in by_category.items()),
                key=lambda c: c["total"],
                reverse=True,
            ),
        },
        "weather": {"home_city": user.home_city, "data": weather, "error": weather_error},
        "pending_actions": pending_count or 0,
    }


def _clock(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M")


def briefing_text(overview: dict[str, Any]) -> str:
    """The morning briefing as plain German prose - built from the overview, not the LLM, so it's
    instant, always available (even with Ollama down) and can't make things up."""
    parts = [f"Guten Morgen, {overview['display_name']}."]

    weather = overview["weather"]["data"]
    if weather:
        today = weather["daily"][0] if weather.get("daily") else None
        line = f"In {weather['location']} sind es gerade {round(weather['current_temperature'])} Grad, {weather['current_condition']}"
        if today:
            line += f", heute zwischen {round(today['temp_min'])} und {round(today['temp_max'])} Grad"
        parts.append(line + ".")

    cal = overview["calendar"]
    if cal["connected"] and not cal["error"]:
        events = cal["events"]
        if not events:
            parts.append("Heute stehen keine Termine an.")
        else:
            described = [
                e["title"] if e["all_day"] else f"um {_clock(e['start'])} {e['title']}" for e in events[:4]
            ]
            more = f" und {len(events) - 4} weitere" if len(events) > 4 else ""
            noun = "Termin" if len(events) == 1 else "Termine"
            parts.append(f"Heute {len(events)} {noun}: {', '.join(described)}{more}.")

    today_iso = overview["today"]
    todays_reminders = [r for r in overview["reminders"] if r["next_at"].startswith(today_iso)]
    if todays_reminders:
        parts.append(
            "Erinnerungen heute: "
            + ", ".join(f"{_clock(r['next_at'])} {r['label']}" for r in todays_reminders)
            + "."
        )

    for b in overview["birthdays"]:
        if b["days_until"] == 0:
            parts.append(f"{b['name']} hat heute Geburtstag" + (f" und wird {b['turns']}." if b["turns"] else "."))

    open_lists = [lst for lst in overview["lists"] if lst["open_count"]]
    if open_lists:
        parts.append(
            "Offen: " + ", ".join(f"{lst['open_count']} auf „{lst['name']}“" for lst in open_lists[:3]) + "."
        )

    if overview["pending_actions"]:
        n = overview["pending_actions"]
        parts.append(f"{n} {'Aktion wartet' if n == 1 else 'Aktionen warten'} auf deine Bestätigung.")

    return " ".join(parts)

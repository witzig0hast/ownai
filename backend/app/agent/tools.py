from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services import calendar_service

ToolHandler = Callable[[AsyncSession, User, dict[str, Any]], Awaitable[Any]]


async def _calendar_list_events(db: AsyncSession, user: User, arguments: dict[str, Any]) -> Any:
    now = datetime.now(timezone.utc)
    start = _parse_dt(arguments.get("start")) or now
    end = _parse_dt(arguments.get("end")) or (start + timedelta(days=7))
    events = await calendar_service.list_events(db, user, start, end)
    return [{**e, "start": e["start"].isoformat(), "end": e["end"].isoformat()} for e in events]


async def _calendar_create_event(db: AsyncSession, user: User, arguments: dict[str, Any]) -> Any:
    start = _parse_dt(arguments["start"])
    end = _parse_dt(arguments.get("end")) or (start + timedelta(hours=1))
    event = await calendar_service.create_event(
        db, user, title=arguments["title"], start=start, end=end, location=arguments.get("location")
    )
    return {**event, "start": event["start"].isoformat(), "end": event["end"].isoformat()}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# JSON schemas in Ollama's OpenAI-style tool format (see app/services/ollama_client.py).
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calendar_list_events",
            "description": (
                "Listet Kalendertermine des Nutzers in einem Zeitraum auf. "
                "Nutze das, um zu prüfen, ob der Nutzer zu einer Zeit schon etwas vorhat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO-8601-Startzeitpunkt, z.B. 2026-09-25T00:00:00Z"},
                    "end": {"type": "string", "description": "ISO-8601-Endzeitpunkt"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create_event",
            "description": "Legt einen neuen Kalendertermin im Kalender des Nutzers an.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titel des Termins"},
                    "start": {"type": "string", "description": "ISO-8601-Startzeitpunkt"},
                    "end": {"type": "string", "description": "ISO-8601-Endzeitpunkt"},
                    "location": {"type": "string", "description": "Ort (optional)"},
                },
                "required": ["title", "start"],
            },
        },
    },
]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "calendar_list_events": _calendar_list_events,
    "calendar_create_event": _calendar_create_event,
}

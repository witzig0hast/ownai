from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services import calendar_service, home_assistant_service

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


async def _home_assistant_list_entities(db: AsyncSession, user: User, arguments: dict[str, Any]) -> Any:
    return await home_assistant_service.list_entities(db, user, domain=arguments.get("domain"))


async def _home_assistant_call_service(db: AsyncSession, user: User, arguments: dict[str, Any]) -> Any:
    return await home_assistant_service.call_service(
        db,
        user,
        entity_id=arguments["entity_id"],
        service=arguments["service"],
        data=arguments.get("data"),
    )


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
    {
        "type": "function",
        "function": {
            "name": "home_assistant_list_entities",
            "description": (
                "Listet Smart-Home-Geräte (Home Assistant Entities) des Nutzers auf, mit aktuellem Zustand. "
                "Nutze das, um zu prüfen, was es gibt oder wie der aktuelle Status ist, bevor du etwas steuerst."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": (
                            "Optional: nur diese Art von Gerät auflisten, z.B. 'light', 'switch', 'climate', "
                            "'cover', 'fan', 'lock', 'media_player'. Weggelassen = alle."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "home_assistant_call_service",
            "description": (
                "Steuert ein Smart-Home-Gerät (Home Assistant) — z.B. Licht an/aus, Rollladen hoch/runter, "
                "Temperatur setzen. entity_id vorher über home_assistant_list_entities herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "z.B. 'light.wohnzimmer'"},
                    "service": {
                        "type": "string",
                        "description": "Home-Assistant-Service-Name, z.B. 'turn_on', 'turn_off', 'toggle', 'set_temperature'",
                    },
                    "data": {
                        "type": "object",
                        "description": "Zusätzliche Parameter für den Service, z.B. {\"temperature\": 21} bei set_temperature",
                    },
                },
                "required": ["entity_id", "service"],
            },
        },
    },
]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "calendar_list_events": _calendar_list_events,
    "calendar_create_event": _calendar_create_event,
    "home_assistant_list_entities": _home_assistant_list_entities,
    "home_assistant_call_service": _home_assistant_call_service,
}

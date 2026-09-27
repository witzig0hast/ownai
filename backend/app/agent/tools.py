from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services import calendar_service, home_assistant_service, timer_service
from app.utils import ensure_utc

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


async def _set_timer(db: AsyncSession, user: User, arguments: dict[str, Any]) -> Any:
    timer = await timer_service.create_timer(
        db, user, duration_seconds=int(arguments["duration_seconds"]), label=arguments.get("label")
    )
    return {"id": timer.id, "label": timer.label, "ends_at": ensure_utc(timer.ends_at).isoformat()}


async def _list_timers(db: AsyncSession, user: User, _arguments: dict[str, Any]) -> Any:
    now = datetime.now(timezone.utc)
    timers = await timer_service.list_active_timers(db, user)
    return [
        {
            "id": t.id,
            "label": t.label,
            "ends_at": ensure_utc(t.ends_at).isoformat(),
            "remaining_seconds": max(0, int((ensure_utc(t.ends_at) - now).total_seconds())),
        }
        for t in timers
    ]


async def _cancel_timer(db: AsyncSession, user: User, arguments: dict[str, Any]) -> Any:
    timer = await timer_service.cancel_timer(db, user, arguments["timer_id"])
    return {"id": timer.id, "cancelled": True}


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
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": (
                "Stellt einen Countdown-Timer. Rechne die gewünschte Dauer (z.B. '5 Minuten', "
                "'eine halbe Stunde', '90 Sekunden') in Sekunden um. Der Timer läuft geräteübergreifend: "
                "er wird angezeigt/benachrichtigt auf jedem Gerät, auf dem der Nutzer OwnAI offen hat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {"type": "integer", "description": "Dauer in Sekunden, z.B. 300 für 5 Minuten"},
                    "label": {"type": "string", "description": "Kurze Beschreibung, z.B. 'Nudeln', 'Eier kochen' (optional)"},
                },
                "required": ["duration_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_timers",
            "description": "Listet alle laufenden Timer des Nutzers auf, mit verbleibender Zeit in Sekunden.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_timer",
            "description": "Bricht einen laufenden Timer ab. timer_id vorher über list_timers herausfinden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timer_id": {"type": "string", "description": "ID des Timers (aus list_timers)"},
                },
                "required": ["timer_id"],
            },
        },
    },
]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "calendar_list_events": _calendar_list_events,
    "calendar_create_event": _calendar_create_event,
    "home_assistant_list_entities": _home_assistant_list_entities,
    "home_assistant_call_service": _home_assistant_call_service,
    "set_timer": _set_timer,
    "list_timers": _list_timers,
    "cancel_timer": _cancel_timer,
}

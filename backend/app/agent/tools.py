from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, User
from app.schemas.automation import AutomationCreateRequest, AutomationUpdateRequest
from app.schemas.contact import ContactCreateRequest, ContactUpdateRequest
from app.schemas.list import ListCreateRequest, ListItemCreateRequest, ListItemUpdateRequest
from app.schemas.reminder import ReminderCreateRequest, ReminderUpdateRequest
from app.services import (
    agent_bus_service,
    automation_service,
    calendar_service,
    contact_service,
    email_service,
    file_service,
    home_assistant_service,
    list_service,
    memory_service,
    reminder_service,
    timer_service,
)
from app.utils import ensure_utc

# Every handler gets the current conversation too (not just db/user) - needed by create_file,
# which scopes files per-conversation; the others just ignore it (leading underscore).
ToolHandler = Callable[[AsyncSession, User, Conversation, dict[str, Any]], Awaitable[Any]]


async def _calendar_list_events(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    now = datetime.now(timezone.utc)
    start = _parse_dt(arguments.get("start")) or now
    end = _parse_dt(arguments.get("end")) or (start + timedelta(days=7))
    events = await calendar_service.list_events(db, user, start, end)
    return [{**e, "start": e["start"].isoformat(), "end": e["end"].isoformat()} for e in events]


async def _calendar_create_event(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    start = _parse_dt(arguments["start"])
    end = _parse_dt(arguments.get("end")) or (start + timedelta(hours=1))
    event = await calendar_service.create_event(
        db, user, title=arguments["title"], start=start, end=end, location=arguments.get("location")
    )
    return {**event, "start": event["start"].isoformat(), "end": event["end"].isoformat()}


async def _home_assistant_list_entities(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    return await home_assistant_service.list_entities(db, user, domain=arguments.get("domain"))


async def _home_assistant_call_service(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    return await home_assistant_service.call_service(
        db,
        user,
        entity_id=arguments["entity_id"],
        service=arguments["service"],
        data=arguments.get("data"),
    )


async def _set_timer(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    timer = await timer_service.create_timer(
        db, user, duration_seconds=int(arguments["duration_seconds"]), label=arguments.get("label")
    )
    return {"id": timer.id, "label": timer.label, "ends_at": ensure_utc(timer.ends_at).isoformat()}


async def _list_timers(
    db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]
) -> Any:
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


async def _cancel_timer(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    timer = await timer_service.cancel_timer(db, user, arguments["timer_id"])
    return {"id": timer.id, "cancelled": True}


async def _create_file(db: AsyncSession, user: User, conversation: Conversation, arguments: dict[str, Any]) -> Any:
    record = await file_service.create_file(
        db,
        user,
        conversation,
        filename=arguments["filename"],
        content=arguments["content"],
        file_format=arguments.get("format", "txt"),
    )
    return {
        "id": record.id,
        "filename": record.filename,
        "size_bytes": record.size_bytes,
        "download_url": f"/api/v1/chat/conversations/{conversation.id}/files/{record.id}",
    }


async def _send_email(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    await email_service.send_email(
        db, user, to=arguments["to"], subject=arguments["subject"], body=arguments["body"]
    )
    return {"sent": True, "to": arguments["to"]}


async def _agent_bus_send_message(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    message = await agent_bus_service.send_message(
        db,
        user,
        from_agent=None,
        to_name=arguments["to"],
        kind=arguments["kind"],
        content=arguments.get("content"),
        task_type=arguments.get("task_type"),
        payload=arguments.get("payload"),
    )
    return {"id": message.id, "to": message.to_label, "status": message.status}


async def _agent_bus_list_agents(
    db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]
) -> Any:
    agents = await agent_bus_service.list_agents(db, user)
    return [{"name": a.name, "description": a.description} for a in agents]


async def _spawn_subagent(db: AsyncSession, user: User, conversation: Conversation, arguments: dict[str, Any]) -> Any:
    from app.agent.subagent import run_subagent  # lazy: subagent.py imports TOOL_SCHEMAS/TOOL_HANDLERS from here

    return await run_subagent(db, user, conversation, task=arguments["task"])


async def _remember_fact(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    memory = await memory_service.add_memory(db, user, arguments["content"])
    return {"id": memory.id, "content": memory.content}


async def _list_memories(
    db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]
) -> Any:
    memories = await memory_service.list_memories(db, user)
    return [{"id": m.id, "content": m.content} for m in memories]


async def _forget_fact(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    await memory_service.delete_memory(db, user, arguments["memory_id"])
    return {"forgotten": True}


def _contact_dict(contact: Any) -> dict[str, Any]:
    return {
        "id": contact.id,
        "name": contact.name,
        "phone": contact.phone,
        "email": contact.email,
        "birthday_month": contact.birthday_month,
        "birthday_day": contact.birthday_day,
        "birthday_year": contact.birthday_year,
        "notes": contact.notes,
    }


async def _add_contact(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    payload = ContactCreateRequest(
        name=arguments["name"],
        phone=arguments.get("phone"),
        email=arguments.get("email"),
        birthday_month=arguments.get("birthday_month"),
        birthday_day=arguments.get("birthday_day"),
        birthday_year=arguments.get("birthday_year"),
        notes=arguments.get("notes"),
    )
    contact = await contact_service.add_contact(db, user, payload)
    return _contact_dict(contact)


async def _list_contacts(
    db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]
) -> Any:
    contacts = await contact_service.list_contacts(db, user)
    return [_contact_dict(c) for c in contacts]


async def _update_contact(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    payload = ContactUpdateRequest(
        name=arguments.get("name"),
        phone=arguments.get("phone"),
        email=arguments.get("email"),
        birthday_month=arguments.get("birthday_month"),
        birthday_day=arguments.get("birthday_day"),
        birthday_year=arguments.get("birthday_year"),
        notes=arguments.get("notes"),
    )
    contact = await contact_service.update_contact(db, user, arguments["contact_id"], payload)
    return _contact_dict(contact)


async def _delete_contact(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    await contact_service.delete_contact(db, user, arguments["contact_id"])
    return {"deleted": True}


def _reminder_dict(reminder: Any) -> dict[str, Any]:
    return {
        "id": reminder.id,
        "label": reminder.label,
        "recurrence": reminder.recurrence,
        "hour": reminder.hour,
        "minute": reminder.minute,
        "weekday": reminder.weekday,
        "day_of_month": reminder.day_of_month,
        "active": reminder.active,
    }


async def _add_reminder(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    payload = ReminderCreateRequest(
        label=arguments["label"],
        recurrence=arguments["recurrence"],
        hour=arguments["hour"],
        minute=arguments["minute"],
        weekday=arguments.get("weekday"),
        day_of_month=arguments.get("day_of_month"),
    )
    reminder = await reminder_service.add_reminder(db, user, payload)
    return _reminder_dict(reminder)


async def _list_reminders(
    db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]
) -> Any:
    reminders = await reminder_service.list_reminders(db, user)
    return [_reminder_dict(r) for r in reminders]


async def _update_reminder(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    payload = ReminderUpdateRequest(
        label=arguments.get("label"),
        recurrence=arguments.get("recurrence"),
        hour=arguments.get("hour"),
        minute=arguments.get("minute"),
        weekday=arguments.get("weekday"),
        day_of_month=arguments.get("day_of_month"),
        active=arguments.get("active"),
    )
    reminder = await reminder_service.update_reminder(db, user, arguments["reminder_id"], payload)
    return _reminder_dict(reminder)


async def _delete_reminder(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    await reminder_service.delete_reminder(db, user, arguments["reminder_id"])
    return {"deleted": True}


def _automation_dict(automation: Any) -> dict[str, Any]:
    return {
        "id": automation.id,
        "entity_id": automation.entity_id,
        "trigger_state": automation.trigger_state,
        "message": automation.message,
        "active": automation.active,
    }


async def _add_automation(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    payload = AutomationCreateRequest(
        entity_id=arguments["entity_id"], trigger_state=arguments["trigger_state"], message=arguments["message"]
    )
    automation = await automation_service.add_automation(db, user, payload)
    return _automation_dict(automation)


async def _list_automations(
    db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]
) -> Any:
    automations = await automation_service.list_automations(db, user)
    return [_automation_dict(a) for a in automations]


async def _update_automation(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    payload = AutomationUpdateRequest(
        entity_id=arguments.get("entity_id"),
        trigger_state=arguments.get("trigger_state"),
        message=arguments.get("message"),
        active=arguments.get("active"),
    )
    automation = await automation_service.update_automation(db, user, arguments["automation_id"], payload)
    return _automation_dict(automation)


async def _delete_automation(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    await automation_service.delete_automation(db, user, arguments["automation_id"])
    return {"deleted": True}


def _list_dict(todo_list: Any) -> dict[str, Any]:
    return {
        "id": todo_list.id,
        "name": todo_list.name,
        "kind": todo_list.kind,
        "items": [{"id": i.id, "content": i.content, "done": i.done} for i in todo_list.items],
    }


async def _create_list(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    payload = ListCreateRequest(name=arguments["name"], kind=arguments["kind"])
    todo_list = await list_service.add_list(db, user, payload)
    return _list_dict(todo_list)


async def _list_lists(db: AsyncSession, user: User, _conversation: Conversation, _arguments: dict[str, Any]) -> Any:
    lists = await list_service.list_lists(db, user)
    return [_list_dict(todo_list) for todo_list in lists]


async def _delete_list(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    await list_service.delete_list(db, user, arguments["list_id"])
    return {"deleted": True}


async def _add_list_item(db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]) -> Any:
    payload = ListItemCreateRequest(content=arguments["content"])
    todo_list = await list_service.add_item(db, user, arguments["list_id"], payload)
    return _list_dict(todo_list)


async def _update_list_item(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    payload = ListItemUpdateRequest(content=arguments.get("content"), done=arguments.get("done"))
    todo_list = await list_service.update_item(db, user, arguments["list_id"], arguments["item_id"], payload)
    return _list_dict(todo_list)


async def _delete_list_item(
    db: AsyncSession, user: User, _conversation: Conversation, arguments: dict[str, Any]
) -> Any:
    todo_list = await list_service.delete_item(db, user, arguments["list_id"], arguments["item_id"])
    return _list_dict(todo_list)


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
                "Stellt einen Countdown-Timer. Rechne die vom Nutzer genannte Dauer IMMER SELBST in Sekunden "
                "um, ohne nachzufragen - der Nutzer soll nie selbst rechnen müssen. Beispiele: '5 Minuten' -> "
                "duration_seconds=300, 'eine halbe Stunde' -> 1800, '10 Minuten' -> 600, '90 Sekunden' -> 90, "
                "'2 Stunden' -> 7200. Der Timer läuft geräteübergreifend: er wird angezeigt/benachrichtigt auf "
                "jedem Gerät, auf dem der Nutzer OwnAI offen hat."
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
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": (
                "Erstellt eine Datei (PDF, Text oder Markdown) mit dem angegebenen Inhalt und speichert sie "
                "für diesen Nutzer in dieser Unterhaltung ab. Nutze das, wenn der Nutzer dich bittet, etwas "
                "zu verfassen, aufzuschreiben oder als Dokument/PDF anzulegen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Anzeigename der Datei, z.B. 'Einkaufsliste.pdf'"},
                    "content": {"type": "string", "description": "Vollständiger Textinhalt der Datei"},
                    "format": {
                        "type": "string",
                        "enum": ["pdf", "txt", "md"],
                        "description": "Dateiformat, Standard 'txt'",
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": (
                "Verschickt eine E-Mail über das E-Mail-Konto des Nutzers (persönlich hinterlegt oder "
                "System-Standard). Nutze das nur, wenn der Nutzer dich explizit bittet, eine E-Mail zu senden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Empfänger-E-Mail-Adresse"},
                    "subject": {"type": "string", "description": "Betreff"},
                    "body": {"type": "string", "description": "Nachrichtentext"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agent_bus_list_agents",
            "description": (
                "Listet die vom Nutzer registrierten externen Agents (eigene andere Projekte/Webseiten) "
                "auf, die über den Agent Bus erreichbar sind. Nutze das, bevor du eine Nachricht sendest, "
                "um den richtigen Namen zu kennen."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agent_bus_send_message",
            "description": (
                "Sendet eine Nachricht oder eine strukturierte Aufgabe an einen registrierten externen "
                "Agent (ein anderes Projekt/eine andere Webseite des Nutzers) über den Agent Bus. Nutze "
                "agent_bus_list_agents, um gültige Namen herauszufinden, statt zu raten."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Name des Ziel-Agents (aus agent_bus_list_agents)"},
                    "kind": {"type": "string", "enum": ["text", "task"]},
                    "content": {"type": "string", "description": "Nachrichtentext — erforderlich bei kind='text'"},
                    "task_type": {"type": "string", "description": "Aufgabentyp — erforderlich bei kind='task'"},
                    "payload": {
                        "type": "object",
                        "description": "Zusätzliche Parameter der Aufgabe (bei kind='task')",
                    },
                },
                "required": ["to", "kind"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_subagent",
            "description": (
                "Delegiert eine klar abgegrenzte Teilaufgabe an einen eigenständigen Sub-Agenten, der sie "
                "mit denselben Werkzeugen selbstständig löst und nur das Endergebnis zurückgibt. Nutze das "
                "für Aufgaben mit mehreren eigenen Zwischenschritten, die sich klar von der Hauptunterhaltung "
                "abgrenzen lassen — nicht für einfache Ein-Schritt-Aufrufe, die du direkt selbst erledigen "
                "kannst. Ein Sub-Agent kann selbst keine weiteren Sub-Agents starten."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Klare, in sich abgeschlossene Beschreibung der Teilaufgabe",
                    },
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": (
                "Speichert einen Fakt über den Nutzer dauerhaft (z.B. Vorlieben, wiederkehrende Details, "
                "Kontext), damit du ihn dir in jeder zukünftigen Unterhaltung merkst, ohne dass der Nutzer "
                "es erneut sagen muss. Nutze das proaktiv, wenn der Nutzer etwas über sich erzählt, das "
                "später nützlich sein könnte — nicht für einmalige, unwichtige Details."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Der Fakt, kurz und in sich verständlich formuliert, z.B. 'Mag keine Zwiebeln'",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_memories",
            "description": "Listet alle bisher über den Nutzer gemerkten Fakten auf (mit ihrer ID).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_fact",
            "description": (
                "Löscht einen gemerkten Fakt wieder, z.B. wenn er nicht mehr stimmt oder der Nutzer darum "
                "bittet. memory_id vorher über list_memories herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "ID des Fakts (aus list_memories)"},
                },
                "required": ["memory_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_contact",
            "description": (
                "Legt einen neuen Kontakt an (Name, optional Telefon, E-Mail, Geburtstag, Notizen). "
                "Ist ein Geburtstag bekannt, wird der Nutzer am Tag selbst automatisch per Push daran erinnert."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name des Kontakts"},
                    "phone": {"type": "string", "description": "Telefonnummer, optional"},
                    "email": {"type": "string", "description": "E-Mail-Adresse, optional"},
                    "birthday_month": {"type": "integer", "description": "Geburtstag: Monat (1-12), optional"},
                    "birthday_day": {"type": "integer", "description": "Geburtstag: Tag (1-31), optional"},
                    "birthday_year": {
                        "type": "integer",
                        "description": "Geburtsjahr, optional (nur für die Altersanzeige)",
                    },
                    "notes": {"type": "string", "description": "Freitext-Notizen, optional"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contacts",
            "description": "Listet alle gespeicherten Kontakte des Nutzers auf (mit ihrer ID).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_contact",
            "description": (
                "Ändert Felder eines bestehenden Kontakts. contact_id vorher über list_contacts "
                "herausfinden. Nur angegebene Felder werden geändert."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "ID des Kontakts (aus list_contacts)"},
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "birthday_month": {"type": "integer"},
                    "birthday_day": {"type": "integer"},
                    "birthday_year": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_contact",
            "description": "Löscht einen Kontakt endgültig. contact_id vorher über list_contacts herausfinden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "ID des Kontakts (aus list_contacts)"},
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_reminder",
            "description": (
                "Legt eine wiederkehrende Erinnerung an, die den Nutzer zu einer festen Uhrzeit "
                "per Push benachrichtigt — täglich, wöchentlich an einem Wochentag, oder monatlich an "
                "einem Tag des Monats. Für einmalige Countdowns stattdessen set_timer nutzen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Was die Erinnerung sagen soll"},
                    "recurrence": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                    "hour": {"type": "integer", "description": "Stunde (0-23)"},
                    "minute": {"type": "integer", "description": "Minute (0-59)"},
                    "weekday": {
                        "type": "string",
                        "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                        "description": "Nur bei recurrence='weekly' erforderlich",
                    },
                    "day_of_month": {
                        "type": "integer",
                        "description": "Tag des Monats (1-31), nur bei recurrence='monthly' erforderlich",
                    },
                },
                "required": ["label", "recurrence", "hour", "minute"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "Listet alle wiederkehrenden Erinnerungen des Nutzers auf (mit ihrer ID).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_reminder",
            "description": (
                "Ändert Felder einer bestehenden Erinnerung, z.B. um sie zu pausieren (active=false) "
                "oder die Uhrzeit zu ändern. reminder_id vorher über list_reminders herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "string", "description": "ID der Erinnerung (aus list_reminders)"},
                    "label": {"type": "string"},
                    "recurrence": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                    "hour": {"type": "integer"},
                    "minute": {"type": "integer"},
                    "weekday": {"type": "string", "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
                    "day_of_month": {"type": "integer"},
                    "active": {"type": "boolean"},
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_reminder",
            "description": "Löscht eine Erinnerung endgültig. reminder_id vorher über list_reminders herausfinden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "string", "description": "ID der Erinnerung (aus list_reminders)"},
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_automation",
            "description": (
                "Legt eine Automatisierung an, die den Nutzer per Push benachrichtigt, sobald eine "
                "Home-Assistant-Entität einen bestimmten Zustand erreicht (z.B. 'Tür wird aufgeschlossen'). "
                "Nutze vorher home_assistant_list_entities, um die richtige entity_id und mögliche "
                "Zustandswerte herauszufinden. Feuert nur bei Zustandswechsel, nicht wiederholt, solange "
                "der Zustand bestehen bleibt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "Home-Assistant entity_id, z.B. 'lock.haustuer'"},
                    "trigger_state": {"type": "string", "description": "Zustand, der die Push auslöst, z.B. 'unlocked'"},
                    "message": {"type": "string", "description": "Text der Push-Benachrichtigung"},
                },
                "required": ["entity_id", "trigger_state", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_automations",
            "description": "Listet alle Automatisierungen des Nutzers auf (mit ihrer ID).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_automation",
            "description": (
                "Ändert Felder einer bestehenden Automatisierung, z.B. um sie zu pausieren (active=false). "
                "automation_id vorher über list_automations herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_id": {"type": "string", "description": "ID der Automatisierung (aus list_automations)"},
                    "entity_id": {"type": "string"},
                    "trigger_state": {"type": "string"},
                    "message": {"type": "string"},
                    "active": {"type": "boolean"},
                },
                "required": ["automation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_automation",
            "description": (
                "Löscht eine Automatisierung endgültig. automation_id vorher über list_automations herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "automation_id": {"type": "string", "description": "ID der Automatisierung (aus list_automations)"},
                },
                "required": ["automation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_list",
            "description": "Legt eine neue Liste an - eine Todo-Liste oder eine Einkaufsliste.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name der Liste, z.B. 'Einkaufsliste'"},
                    "kind": {"type": "string", "enum": ["todo", "shopping"]},
                },
                "required": ["name", "kind"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lists",
            "description": "Listet alle Listen des Nutzers mitsamt ihrer Einträge auf (mit IDs).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_list",
            "description": "Löscht eine ganze Liste inkl. aller Einträge. list_id vorher über list_lists herausfinden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "list_id": {"type": "string", "description": "ID der Liste (aus list_lists)"},
                },
                "required": ["list_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_list_item",
            "description": "Fügt einen Eintrag zu einer bestehenden Liste hinzu. list_id vorher über list_lists herausfinden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "list_id": {"type": "string", "description": "ID der Liste (aus list_lists)"},
                    "content": {"type": "string", "description": "Text des Eintrags, z.B. 'Milch'"},
                },
                "required": ["list_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_list_item",
            "description": (
                "Ändert einen Eintrag - z.B. als erledigt/abgehakt markieren (done=true) oder den Text ändern. "
                "list_id und item_id vorher über list_lists herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "list_id": {"type": "string", "description": "ID der Liste (aus list_lists)"},
                    "item_id": {"type": "string", "description": "ID des Eintrags (aus list_lists)"},
                    "content": {"type": "string"},
                    "done": {"type": "boolean"},
                },
                "required": ["list_id", "item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_list_item",
            "description": (
                "Löscht einen einzelnen Eintrag aus einer Liste. list_id und item_id vorher über "
                "list_lists herausfinden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "list_id": {"type": "string", "description": "ID der Liste (aus list_lists)"},
                    "item_id": {"type": "string", "description": "ID des Eintrags (aus list_lists)"},
                },
                "required": ["list_id", "item_id"],
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
    "create_file": _create_file,
    "send_email": _send_email,
    "spawn_subagent": _spawn_subagent,
    "agent_bus_list_agents": _agent_bus_list_agents,
    "agent_bus_send_message": _agent_bus_send_message,
    "remember_fact": _remember_fact,
    "list_memories": _list_memories,
    "forget_fact": _forget_fact,
    "add_contact": _add_contact,
    "list_contacts": _list_contacts,
    "update_contact": _update_contact,
    "delete_contact": _delete_contact,
    "add_reminder": _add_reminder,
    "list_reminders": _list_reminders,
    "update_reminder": _update_reminder,
    "delete_reminder": _delete_reminder,
    "add_automation": _add_automation,
    "list_automations": _list_automations,
    "update_automation": _update_automation,
    "delete_automation": _delete_automation,
    "create_list": _create_list,
    "list_lists": _list_lists,
    "delete_list": _delete_list,
    "add_list_item": _add_list_item,
    "update_list_item": _update_list_item,
    "delete_list_item": _delete_list_item,
}

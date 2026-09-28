import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent_presets import get_preset, is_valid_preset_key
from app.db.models import AgentLogEntry, PermanentAgent, User
from app.errors import APIError
from app.schemas.permanent_agent import PermanentAgentCreateRequest, PermanentAgentUpdateRequest
from app.services import ollama_client, push_service
from app.utils import ensure_utc

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 5
RECENT_LOG_CONTEXT_LIMIT = 5

# Not a real tool - handled specially in _run_agent_once (see there for why) rather than going
# through the normal TOOL_HANDLERS registry, since it needs to influence *this run's* outcome
# (mark it notable, trigger a push) rather than return a value to feed back into the loop.
_FLAG_FINDING_SCHEMA = {
    "type": "function",
    "function": {
        "name": "flag_finding",
        "description": (
            "Meldet einen Fund, der für den Nutzer wichtig genug ist, um sofort per Push benachrichtigt "
            "zu werden (statt nur im Log zu landen). Nutze das sparsam - nur bei echt Neuem/Relevantem, "
            "nicht bei jedem Lauf."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Kurze, für den Nutzer verständliche Meldung"},
            },
            "required": ["message"],
        },
    },
}


class InvalidPreset(APIError):
    def __init__(self, message: str):
        super().__init__(422, "invalid_preset", message)


class PermanentAgentNotFound(APIError):
    def __init__(self, message: str = "Agent nicht gefunden."):
        super().__init__(404, "not_found", message)


async def add_agent(db: AsyncSession, user: User, payload: PermanentAgentCreateRequest) -> PermanentAgent:
    if not is_valid_preset_key(payload.preset):
        raise InvalidPreset(f"Unbekanntes Preset: {payload.preset!r}")
    agent = PermanentAgent(
        user_id=user.id,
        name=payload.name.strip(),
        preset=payload.preset,
        role_prompt=payload.role_prompt.strip(),
        interval_minutes=payload.interval_minutes,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def list_agents(db: AsyncSession, user: User) -> list[PermanentAgent]:
    result = await db.execute(
        select(PermanentAgent).where(PermanentAgent.user_id == user.id).order_by(PermanentAgent.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_owned_agent(db: AsyncSession, user: User, agent_id: str) -> PermanentAgent:
    agent = await db.get(PermanentAgent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise PermanentAgentNotFound()
    return agent


async def update_agent(
    db: AsyncSession, user: User, agent_id: str, payload: PermanentAgentUpdateRequest
) -> PermanentAgent:
    agent = await _get_owned_agent(db, user, agent_id)
    if payload.name is not None:
        agent.name = payload.name.strip()
    if payload.role_prompt is not None:
        agent.role_prompt = payload.role_prompt.strip()
    if payload.interval_minutes is not None:
        agent.interval_minutes = payload.interval_minutes
    if payload.active is not None:
        agent.active = payload.active
    await db.commit()
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, user: User, agent_id: str) -> None:
    agent = await _get_owned_agent(db, user, agent_id)
    await db.delete(agent)
    await db.commit()


async def list_log_entries(db: AsyncSession, user: User, agent_id: str, limit: int = 50) -> list[AgentLogEntry]:
    await _get_owned_agent(db, user, agent_id)  # raises NotFound if not the user's agent
    result = await db.execute(
        select(AgentLogEntry)
        .where(AgentLogEntry.agent_id == agent_id)
        .order_by(AgentLogEntry.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def due_agents(db: AsyncSession, now: datetime) -> list[PermanentAgent]:
    """Active agents whose interval has elapsed since their last run (or that have never run) -
    used by the scheduler's poll (app/services/scheduler.py). Filtered in Python rather than in
    SQL: `interval_minutes` varies per row, and this app's models are kept dialect-independent
    (see app/db/models.py), so a per-row date-arithmetic WHERE clause would need dialect-specific
    SQL. Fine at the scale of a personal assistant's agent count."""
    result = await db.execute(select(PermanentAgent).where(PermanentAgent.active.is_(True)))
    agents = list(result.scalars().all())
    due = []
    for agent in agents:
        if agent.last_run_at is None:
            due.append(agent)
            continue
        next_due = ensure_utc(agent.last_run_at) + timedelta(minutes=agent.interval_minutes)
        if now >= next_due:
            due.append(agent)
    return due


def _build_system_prompt(agent: PermanentAgent, recent_logs: list[AgentLogEntry]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    parts = [
        "Du bist ein permanenter Beobachtungs-Agent von OwnAI mit genau einer Rolle, die dauerhaft "
        "läuft, ohne dass ein Mensch dich gerade anspricht.",
        f"Deine Rolle: {agent.role_prompt}",
        f"Aktuelle Zeit: {now} (UTC).",
        "Führe jetzt einen Beobachtungslauf durch: nutze deine Werkzeuge, um relevante aktuelle "
        "Informationen zu deiner Rolle zu sammeln, und fasse anschließend knapp zusammen, was du "
        "herausgefunden hast (auch wenn es 'nichts Neues' ist). Ist ein Fund wichtig genug für eine "
        "sofortige Benachrichtigung des Nutzers, rufe zusätzlich flag_finding auf.",
        "Du kannst KEINE Rückfrage stellen - es gibt niemanden, der antwortet.",
    ]
    if recent_logs:
        history = "\n".join(f"- ({e.created_at.isoformat()}) {e.content}" for e in reversed(recent_logs))
        parts.append(
            "Deine letzten Beobachtungen (nutze das, um dich nicht zu wiederholen und echte "
            f"Änderungen zu erkennen):\n{history}"
        )
    return "\n\n".join(parts)


async def run_agent_once(db: AsyncSession, user: User, agent: PermanentAgent) -> AgentLogEntry:
    """Runs one headless tool-calling turn for a due PermanentAgent (called from the scheduler's
    _run_permanent_agents job). Modeled closely on app.agent.subagent.run_subagent - same
    iteration cap, same per-call error containment - but with no Conversation (permanent agents
    aren't tied to a chat) and a fixed preset instead of a Skill."""
    from app.agent.tools import TOOL_HANDLERS, TOOL_SCHEMAS  # lazy: tools.py imports this module too

    preset = get_preset(agent.preset)
    tool_names = set(preset.tool_names) if preset else set()
    tools = [s for s in TOOL_SCHEMAS if s["function"]["name"] in tool_names] + [_FLAG_FINDING_SCHEMA]

    recent_logs = await list_log_entries(db, user, agent.id, limit=RECENT_LOG_CONTEXT_LIMIT)
    messages: list[dict[str, Any]] = [{"role": "system", "content": _build_system_prompt(agent, recent_logs)}]

    findings: list[str] = []
    notable = False

    try:
        for _ in range(MAX_AGENT_ITERATIONS):
            response = await ollama_client.chat(messages, tools=tools)
            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                content = response.get("content", "").strip()
                if content:
                    findings.append(content)
                break

            messages.append({"role": "assistant", "content": response.get("content", "")})
            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name")
                arguments = function.get("arguments") or {}

                if name == "flag_finding":
                    notable = True
                    findings.append(str(arguments.get("message", "")))
                    result: object = {"flagged": True}
                elif name not in tool_names or name not in TOOL_HANDLERS:
                    result = {"error": f"Werkzeug '{name}' ist für diesen Agenten nicht verfügbar."}
                else:
                    try:
                        # No Conversation exists for a headless run - safe only because every
                        # preset tool is curated to never touch it (see AgentPreset docstring).
                        result = await TOOL_HANDLERS[name](db, user, None, arguments)  # type: ignore[arg-type]
                    except APIError as exc:
                        result = {"error": exc.message}
                    except Exception as exc:  # noqa: BLE001 - one tool failure must not kill the run
                        result = {"error": str(exc)}

                messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)})
        content_text = "\n".join(findings) if findings else "Kein nennenswertes Ergebnis in diesem Lauf."
    except ollama_client.OllamaError as exc:
        logger.warning("Permanent agent %s run failed: %s", agent.id, exc)
        content_text = f"Fehler: Ollama nicht erreichbar ({exc})"

    entry = AgentLogEntry(agent_id=agent.id, content=content_text, notable=notable)
    db.add(entry)
    agent.last_run_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entry)

    if notable:
        try:
            await push_service.send_push(db, user, title=agent.name, body=content_text[:200])
        except Exception:  # noqa: BLE001 - a failed push must not fail the whole run
            logger.exception("Failed to send push for permanent agent %s", agent.id)

    return entry

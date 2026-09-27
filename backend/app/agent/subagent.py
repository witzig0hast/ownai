import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.skills import get_skill
from app.db.models import Conversation, User
from app.errors import APIError
from app.services import ollama_client

MAX_SUBAGENT_ITERATIONS = 5


async def run_subagent(db: AsyncSession, user: User, conversation: Conversation, task: str) -> dict[str, Any]:
    """Runs a small, independent tool-calling loop for one delegated task (the spawn_subagent
    tool). Capped at a single nesting level by construction: spawn_subagent is never offered to
    the subagent's own loop, so it can never spawn a further subagent. Its own tool calls aren't
    persisted as Messages in the conversation - only its final answer + a trace of what it did
    comes back as the parent tool call's result, so the main history stays readable."""
    from app.agent.tools import TOOL_HANDLERS, TOOL_SCHEMAS  # lazy: tools.py imports this module too

    skill = get_skill(conversation.skill)
    allowed_names = skill.tool_names
    tools = [
        s
        for s in TOOL_SCHEMAS
        if s["function"]["name"] != "spawn_subagent" and (allowed_names is None or s["function"]["name"] in allowed_names)
    ]
    tool_name_set = {t["function"]["name"] for t in tools}

    now = datetime.now(timezone.utc).isoformat()
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "Du bist ein Sub-Agent von OwnAI, beauftragt mit genau einer abgegrenzten Aufgabe. Löse "
                "sie eigenständig mit den verfügbaren Werkzeugen und antworte am Ende knapp mit dem "
                "Ergebnis, nicht mit den Zwischenschritten. "
                f"Die aktuelle Zeit ist {now} (UTC). "
                "Wichtig: du kannst KEINE Rückfrage an den Nutzer stellen — es gibt niemanden, der "
                "antwortet. Ist die Aufgabe unterspezifiziert, triff eine vernünftige Annahme, erledige "
                "die Aufgabe damit, und nenne die Annahme kurz in deiner Antwort, statt nachzufragen."
            ),
        },
        {"role": "user", "content": task},
    ]

    steps: list[dict[str, Any]] = []
    final_content = ""

    for _ in range(MAX_SUBAGENT_ITERATIONS):
        response = await ollama_client.chat(messages, tools=tools)
        tool_calls = response.get("tool_calls") or []
        if not tool_calls:
            final_content = response.get("content", "")
            break

        messages.append({"role": "assistant", "content": response.get("content", "")})
        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments") or {}
            handler = TOOL_HANDLERS.get(name)

            if name not in tool_name_set:
                result: object = {"error": f"Werkzeug '{name}' ist für Sub-Agents nicht verfügbar."}
            elif handler is None:
                result = {"error": f"Unbekanntes Werkzeug: {name}"}
            else:
                try:
                    result = await handler(db, user, conversation, arguments)
                except APIError as exc:
                    result = {"error": exc.message}
                except Exception as exc:  # noqa: BLE001 - tool failures must not crash the subagent loop
                    result = {"error": str(exc)}

            steps.append({"tool": name, "arguments": arguments, "result": result})
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)})
    else:
        final_content = "Sub-Agent konnte die Aufgabe nach mehreren Werkzeugaufrufen nicht abschließen."

    return {"answer": final_content, "steps": steps}

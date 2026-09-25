import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import TOOL_HANDLERS, TOOL_SCHEMAS
from app.db.models import Conversation, Message, User
from app.errors import APIError
from app.services import ollama_client

MAX_TOOL_ITERATIONS = 5


def _system_prompt() -> str:
    now = datetime.now(timezone.utc).isoformat()
    return (
        "Du bist OwnAI, ein persönlicher KI-Assistent, der lokal und privat für einen einzelnen Nutzer läuft. "
        "Antworte auf Deutsch, es sei denn der Nutzer schreibt in einer anderen Sprache. "
        f"Die aktuelle Zeit ist {now} (UTC). "
        "Du hast Zugriff auf Werkzeuge (Kalender). Nutze sie, wenn eine Anfrage Kalenderdaten braucht oder "
        "einen Termin anlegen soll — rate nichts, prüfe stattdessen über die Werkzeuge. "
        "Antworte knapp und konkret."
    )


async def run_turn(db: AsyncSession, user: User, conversation: Conversation, user_content: str) -> Message:
    user_message = Message(conversation_id=conversation.id, role="user", content=user_content)
    db.add(user_message)
    await db.flush()

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    ollama_messages: list[dict] = [{"role": "system", "content": _system_prompt()}]
    for past_message in history:
        ollama_messages.append({"role": past_message.role, "content": past_message.content})

    collected_tool_calls: list[dict] = []
    final_content = ""

    for _ in range(MAX_TOOL_ITERATIONS):
        response_message = await ollama_client.chat(ollama_messages, tools=TOOL_SCHEMAS)
        tool_calls = response_message.get("tool_calls") or []

        if not tool_calls:
            final_content = response_message.get("content", "")
            break

        ollama_messages.append({"role": "assistant", "content": response_message.get("content", "")})

        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments") or {}
            handler = TOOL_HANDLERS.get(name)

            if handler is None:
                result: object = {"error": f"Unbekanntes Werkzeug: {name}"}
            else:
                try:
                    result = await handler(db, user, arguments)
                except APIError as exc:
                    result = {"error": exc.message}
                except Exception as exc:  # noqa: BLE001 - tool failures must not crash the chat turn
                    result = {"error": str(exc)}

            collected_tool_calls.append({"tool": name, "arguments": arguments, "result": result})
            ollama_messages.append(
                {"role": "tool", "tool_name": name, "content": json.dumps(result, default=str)}
            )
    else:
        final_content = (
            "Ich konnte die Anfrage nach mehreren Werkzeugaufrufen nicht abschließen. "
            "Bitte formuliere sie genauer oder versuche es erneut."
        )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=final_content,
        tool_calls=collected_tool_calls or None,
    )
    db.add(assistant_message)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(assistant_message)
    return assistant_message

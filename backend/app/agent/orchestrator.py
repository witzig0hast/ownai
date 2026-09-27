import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.skills import Skill, get_skill
from app.agent.tools import TOOL_HANDLERS, TOOL_SCHEMAS
from app.db.models import Conversation, Message, User
from app.errors import APIError
from app.services import ollama_client

MAX_TOOL_ITERATIONS = 5


def _tools_for_skill(skill: Skill) -> list[dict]:
    if skill.tool_names is None:
        return TOOL_SCHEMAS
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in skill.tool_names]


def _system_prompt(skill: Skill) -> str:
    now = datetime.now(timezone.utc).isoformat()
    base = (
        "Du bist OwnAI, der persönliche Assistent des Nutzers. Das ist deine Identität, kein Zusatz zu einer "
        "anderen — du bist nicht 'ein KI-Sprachmodell', das zufällig OwnAI heißt, sondern OwnAI, Punkt. "
        "Fragt dich der Nutzer, was/wer du bist, antworte als sein persönlicher Assistent, nicht mit "
        "Formulierungen wie 'Ich bin ein KI-Modell/Sprachmodell/large language model' — das ist technisch "
        "korrekt, aber nicht die Antwort, die hier erwartet wird. Erwähne auch nicht, auf welchem "
        "zugrundeliegenden Modell (Hermes, Llama, o.ä.) du basierst, außer der Nutzer fragt explizit danach. "
        "Antworte auf Deutsch, es sei denn der Nutzer schreibt in einer anderen Sprache. "
        f"Die aktuelle Zeit ist {now} (UTC). "
        "Du hast Zugriff auf Werkzeuge (Kalender, Smart-Home-Geräte über Home Assistant, Timer, Dateien "
        "erstellen, E-Mails versenden). Nutze sie aktiv, wenn eine Anfrage das braucht — rate nichts, "
        "prüfe/handle stattdessen über die Werkzeuge. "
        "Insbesondere: wenn der Nutzer einen Timer/Wecker/Countdown möchte ('stell mir einen Timer auf 5 "
        "Minuten', 'weck mich in einer halben Stunde'), nutze IMMER set_timer, statt zu sagen, dass du das "
        "nicht kannst — du kannst es. Wenn der Nutzer dich bittet, etwas aufzuschreiben, zu verfassen oder "
        "als Dokument/PDF anzulegen, nutze create_file. Wenn er dich explizit bittet, eine E-Mail zu senden, "
        "nutze send_email. Für eine Teilaufgabe mit mehreren eigenen Zwischenschritten, die sich klar "
        "abgrenzen lässt, kannst du spawn_subagent nutzen, statt alles selbst im Detail durchzuführen. "
        "Wichtiges Prinzip: erledige jede Umrechnung, Vorbereitung oder Zwischenschritt, den EIN Werkzeug "
        "selbst braucht, immer selbst (z.B. Zeitangaben in Sekunden umrechnen, Datumsangaben in ISO-8601 "
        "umwandeln) — frag den Nutzer niemals, dir das in einem für Werkzeuge passenden Format zu geben. Der "
        "Nutzer soll nie merken, dass im Hintergrund Werkzeuge mit technischen Parametern aufgerufen werden. "
        "Antworte knapp und konkret, wie ein hilfsbereiter persönlicher Assistent, der wirklich handelt, "
        "nicht wie ein Chatbot, der jede Anfrage mit Disclaimern und langen Erklärungen einleitet, Fähigkeiten "
        "verneint, die du tatsächlich hast, oder technische Details an den Nutzer zurückgibt, die er nicht "
        "wissen muss."
    )
    if skill.prompt_addition:
        return f"{base}\n\n{skill.prompt_addition}"
    return base


async def run_turn(db: AsyncSession, user: User, conversation: Conversation, user_content: str) -> Message:
    user_message = Message(conversation_id=conversation.id, role="user", content=user_content)
    db.add(user_message)
    await db.flush()

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    skill = get_skill(conversation.skill)
    ollama_messages: list[dict] = [{"role": "system", "content": _system_prompt(skill)}]
    for past_message in history:
        ollama_messages.append({"role": past_message.role, "content": past_message.content})

    collected_tool_calls: list[dict] = []
    final_content = ""
    tools = _tools_for_skill(skill)

    for _ in range(MAX_TOOL_ITERATIONS):
        response_message = await ollama_client.chat(ollama_messages, tools=tools)
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

            if skill.tool_names is not None and name not in skill.tool_names:
                # The model tried a tool outside this conversation's skill - refuse rather than
                # execute, even though the handler exists, since we deliberately didn't offer
                # its schema (a model can still "remember" a tool name from earlier turns).
                result: object = {"error": f"Werkzeug '{name}' ist im Skill '{skill.name}' nicht verfügbar."}
            elif handler is None:
                result = {"error": f"Unbekanntes Werkzeug: {name}"}
            else:
                try:
                    result = await handler(db, user, conversation, arguments)
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

import json
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.skills import Skill, get_skill
from app.agent.tools import TOOL_HANDLERS, TOOL_SCHEMAS
from app.db.models import Conversation, Message, User
from app.errors import APIError
from app.services import memory_service, ollama_client

MAX_TOOL_ITERATIONS = 5

# Caps how much conversation history goes into each Ollama call. Without this, a long-running
# conversation's prompt (and therefore generation latency) grows without bound on every single
# turn - on a slower local GPU this eventually exceeds a reverse proxy's response timeout (504),
# even though the very same model answers quickly early in a fresh conversation. Older messages
# are simply dropped from the prompt, not from the DB/UI - the user still sees full history.
MAX_HISTORY_MESSAGES_IN_PROMPT = 40

_INTERNAL_API_PATH_RE = re.compile(r"/api/v1/\S+")


def _strip_internal_urls(text: str) -> str:
    """Local models sometimes ignore the system prompt's "never mention tool-result URLs"
    instruction and echo a tool result's raw download_url/path back in their reply (e.g. after
    create_file). That's confusing text at best (the client already renders a download button
    from tool_calls, see the web app's Artifact Panel) and actively bad when read aloud in
    Voice, so this is a hard guarantee, not just a prompt ask."""
    cleaned = _INTERNAL_API_PATH_RE.sub("", text)
    return re.sub(r" {2,}", " ", cleaned).strip()


def _tools_for_skill(skill: Skill) -> list[dict]:
    if skill.tool_names is None:
        return TOOL_SCHEMAS
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in skill.tool_names]


def _system_prompt(skill: Skill, memories: list[str]) -> str:
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
        "Du hast Zugriff auf Werkzeuge in folgenden Bereichen: Kalender, Smart-Home-Geräte über Home "
        "Assistant, Timer/Wecker, Dateien erstellen, E-Mails versenden, Kontakte, Erinnerungen, "
        "Automationen (wiederkehrende oder ausgelöste Aktionen), Listen (z.B. Einkaufslisten, To-dos), "
        "Ausgaben-Tracking, Wetter, Web-Suche, RSS-Feeds, Webseiten zusammenfassen/speichern (Web-Clipper), "
        "eigene Notizen über den Nutzer merken, Nachrichten an eigene andere Projekte/Webseiten (Agent Bus) "
        "und dauerhafte Hintergrund-Agenten (Permanent Agents), die eigenständig eine feste Rolle "
        "weiterverfolgen. Nutze diese Werkzeuge aktiv, wenn eine konkrete Anfrage das braucht — rate nichts, "
        "prüfe/handle stattdessen über die Werkzeuge. "
        "Wenn der Nutzer dich fragt, was du kannst, welche Funktionen/Fähigkeiten du hast, oder etwas "
        "Ähnliches ('was kannst du alles', 'was kann ich mit dir machen') — das ist eine Meta-Frage über "
        "dich selbst, keine konkrete Aufgabe. Antworte direkt aus der obigen Liste heraus, in eigenen "
        "Worten, kurz, natürlich und nach Alltagsnutzen gruppiert (z.B. 'ich kann dir bei deinem Kalender "
        "und Terminen helfen, dein Smart Home steuern, Erinnerungen und Timer setzen, Einkaufslisten "
        "führen, ...'). Rufe dafür NIEMALS ein Werkzeug auf (insbesondere nicht "
        "home_assistant_list_entities, list_contacts, list_permanent_agents o.ä.), um dir erst Beispiele "
        "zu 'holen' — das liefert rohe technische IDs/Daten, die den Nutzer nicht interessieren und die "
        "Antwort unpraktisch und umständlich machen. Nur wenn der Nutzer nach konkreten, aktuellen Daten "
        "fragt (z.B. 'welche Geräte habe ich in Home Assistant?', 'was steht in meinem Kalender?'), nutze "
        "das passende Werkzeug. "
        "Insbesondere: wenn der Nutzer einen Timer/Wecker/Countdown möchte ('stell mir einen Timer auf 5 "
        "Minuten', 'weck mich in einer halben Stunde'), nutze IMMER set_timer, statt zu sagen, dass du das "
        "nicht kannst — du kannst es. Wenn der Nutzer dich bittet, etwas aufzuschreiben, zu verfassen oder "
        "als Dokument/PDF anzulegen, nutze create_file. Wenn er dich explizit bittet, eine E-Mail zu senden, "
        "nutze send_email. Für eine Teilaufgabe mit mehreren eigenen Zwischenschritten, die sich klar "
        "abgrenzen lässt, kannst du spawn_subagent nutzen, statt alles selbst im Detail durchzuführen. "
        "Für Berechnungen, Datenauswertungen oder kleine Skripte kannst du Python-Code in einem ```python "
        "Codeblock schreiben — der Nutzer bekommt dazu im Chat einen 'Ausführen'-Button, der den Code direkt "
        "im Browser ausführt (nichts davon läuft auf einem Server). Erkläre das dem Nutzer nicht extra, "
        "schreib einfach den Codeblock. Für Nachrichten oder Aufgaben an eigene andere Projekte/Webseiten "
        "des Nutzers (Agent Bus) nutze agent_bus_list_agents/agent_bus_send_message. "
        "Wichtiges Prinzip: erledige jede Umrechnung, Vorbereitung oder Zwischenschritt, den EIN Werkzeug "
        "selbst braucht, immer selbst (z.B. Zeitangaben in Sekunden umrechnen, Datumsangaben in ISO-8601 "
        "umwandeln) — frag den Nutzer niemals, dir das in einem für Werkzeuge passenden Format zu geben. Der "
        "Nutzer soll nie merken, dass im Hintergrund Werkzeuge mit technischen Parametern aufgerufen werden. "
        "Erwähne NIEMALS URLs, Dateipfade oder IDs aus einem Werkzeug-Ergebnis in deiner Antwort (z.B. nach "
        "create_file) — die Oberfläche zeigt dafür automatisch einen Download-Button/ein Panel an. Sag "
        "einfach knapp, dass du es erledigt hast (z.B. 'Ich habe die Datei erstellt.'). "
        "Manche Werkzeug-Ergebnisse enthalten ein Feld wie 'note'/'status_hint' mit einer kurzen Anweisung "
        "NUR für dich (z.B. wie du das Ergebnis in Worten fassen sollst). Das ist keine Nachricht, auf die "
        "du reagierst oder die du bestätigst — befolge sie einfach lautlos und antworte dem Nutzer direkt "
        "mit dem eigentlichen Ergebnis. Schreib NIEMALS Sätze wie 'Ok, ich werde...', 'Danke für die "
        "Anleitung' oder wiederhole/paraphrasiere den Anweisungstext selbst — der Nutzer soll nie merken, "
        "dass du überhaupt eine Anweisung bekommen hast. "
        "Antworte knapp und konkret, wie ein hilfsbereiter persönlicher Assistent, der wirklich handelt, "
        "nicht wie ein Chatbot, der jede Anfrage mit Disclaimern und langen Erklärungen einleitet, Fähigkeiten "
        "verneint, die du tatsächlich hast, oder technische Details an den Nutzer zurückgibt, die er nicht "
        "wissen muss. "
        "Halte Antworten standardmäßig SEHR kurz — meist 1-3 Sätze reichen. Keine Einleitung, die nur die "
        "Frage umformuliert ('Klar, hier ist...'), keine Zusammenfassung am Ende, keine Aufzählung aller "
        "Optionen/Details, die niemand verlangt hat. Antworte auf genau das, was gefragt wurde, nicht mehr. "
        "Das gilt besonders in Voice-Gesprächen: jede zusätzliche Antwortlänge wird laut vorgelesen und "
        "kostet echte Wartezeit, bevor der Nutzer überhaupt etwas hört — lieber eine kurze, direkte Antwort "
        "geben und bei Bedarf nachfragen lassen, als von Anfang an alles abzudecken, was noch relevant sein "
        "könnte. Nur wenn der Nutzer explizit um Details, eine Erklärung oder eine lange Liste bittet, "
        "antworte ausführlicher."
    )
    if skill.prompt_addition:
        base = f"{base}\n\n{skill.prompt_addition}"
    if memories:
        facts = "\n".join(f"- {m}" for m in memories)
        base = (
            f"{base}\n\nBekannte Fakten über den Nutzer (von dir selbst gemerkt, nutze sie natürlich in "
            f"deinen Antworten, ohne sie dem Nutzer nochmal vorzulesen oder zu erwähnen, dass du sie "
            f"'gemerkt' hast):\n{facts}"
        )
    return base


async def run_turn(db: AsyncSession, user: User, conversation: Conversation, user_content: str) -> Message:
    user_message = Message(conversation_id=conversation.id, role="user", content=user_content)
    db.add(user_message)
    await db.flush()

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    history = history_result.scalars().all()[-MAX_HISTORY_MESSAGES_IN_PROMPT:]

    skill = get_skill(conversation.skill)
    memories = await memory_service.memories_for_prompt(db, user)
    ollama_messages: list[dict] = [{"role": "system", "content": _system_prompt(skill, memories)}]
    for past_message in history:
        ollama_messages.append({"role": past_message.role, "content": past_message.content})

    collected_tool_calls: list[dict] = []
    final_content = ""
    tools = _tools_for_skill(skill)

    for _ in range(MAX_TOOL_ITERATIONS):
        response_message = await ollama_client.chat(ollama_messages, tools=tools)
        tool_calls = response_message.get("tool_calls") or []

        if not tool_calls:
            final_content = _strip_internal_urls(response_message.get("content", ""))
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
                except KeyError as exc:
                    # A tool handler indexed a required argument the model didn't include
                    # (arguments["foo"], not .get("foo")) - str(KeyError) is just the quoted
                    # key name ("'foo'"), which reads as a cryptic, meaningless error to the
                    # model rather than something it can act on. Spell out what's actually
                    # wrong so it can immediately retry with a complete tool call instead of
                    # getting stuck relaying the raw exception text to the user.
                    result = {
                        "error": (
                            f"Pflicht-Parameter '{exc.args[0]}' fehlt beim Aufruf von '{name}'. "
                            "Rufe das Werkzeug erneut mit allen benötigten Angaben auf."
                        )
                    }
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

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, NotificationRaw, NotificationSuggestion, User
from app.schemas.notifications import NotificationIngestRequest
from app.services import ollama_client, push_service

logger = logging.getLogger(__name__)

_CLASSIFY_SYSTEM_PROMPT = """Du analysierst eine einzelne Smartphone-Benachrichtigung für einen persönlichen \
KI-Assistenten. Entscheide, ob daraus ein hilfreicher Vorschlag folgt: entweder ein zu erkennender \
Kalendertermin (kind=calendar_event) oder eine sinnvolle Antwortvorschlag-Situation (kind=reply_draft). \
Die meisten Benachrichtigungen sind irrelevant (Werbung, System, o.ä.) — dann relevant=false.

Antworte AUSSCHLIESSLICH mit einem einzeiligen JSON-Objekt, ohne weiteren Text, in exakt diesem Schema:
{"relevant": bool, "kind": "calendar_event" | "reply_draft" | null, "summary": string, "payload": object}

Für kind=calendar_event: payload = {"title": string, "start": "ISO-8601", "end": "ISO-8601"}. \
Nimm dabei an, dass "heute" sich auf das mitgelieferte Erstellungsdatum der Benachrichtigung bezieht.
Für kind=reply_draft: payload = {"reply": string}.
Wenn relevant=false: kind=null, payload={}.
"""


async def ingest(db: AsyncSession, device: Device, payload: NotificationIngestRequest) -> NotificationRaw:
    notification = NotificationRaw(
        user_id=device.user_id,
        device_id=device.id,
        package_name=payload.package_name,
        app_label=payload.app_label,
        title=payload.title,
        text=payload.text,
        category=payload.category,
        posted_at=payload.posted_at,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


def _parse_classification(raw_content: str) -> dict | None:
    start = raw_content.find("{")
    end = raw_content.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(raw_content[start : end + 1])
    except json.JSONDecodeError:
        return None


async def classify_and_create_suggestion(db: AsyncSession, notification: NotificationRaw) -> NotificationSuggestion | None:
    """Runs the LLM classifier on a raw notification and, if relevant, persists a suggestion.

    Meant to run as a FastAPI BackgroundTask with its own DB session — failures are logged and swallowed
    so a flaky/unreachable Ollama never surfaces as an error to the (already-responded) ingest request.
    """
    user_prompt = (
        f"App: {notification.app_label} ({notification.package_name})\n"
        f"Titel: {notification.title}\n"
        f"Text: {notification.text}\n"
        f"Empfangen: {notification.posted_at.isoformat()}"
    )

    try:
        response = await ollama_client.chat(
            [
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
    except ollama_client.OllamaError:
        logger.exception(
            "Notification classification failed to reach Ollama (notification_id=%s)", notification.id
        )
        return None

    raw_content = response.get("content", "")
    parsed = _parse_classification(raw_content)
    if parsed is None:
        # The model didn't return anything we could parse as JSON at all - almost always means
        # it ignored the "reply with ONLY JSON" instruction (added a preamble, wrapped it in a
        # ```json code fence with unbalanced braces, etc.). Logged at warning (not silently
        # dropped) with the raw text, since this is otherwise invisible - the notification just
        # never turns into a suggestion and nothing else says why.
        logger.warning(
            "Notification classification returned unparseable content (notification_id=%s): %r",
            notification.id,
            raw_content,
        )
        return None
    if not parsed.get("relevant") or not parsed.get("kind"):
        logger.debug("Notification classified as not relevant (notification_id=%s)", notification.id)
        return None

    suggestion = NotificationSuggestion(
        notification_id=notification.id,
        user_id=notification.user_id,
        kind=parsed["kind"],
        summary=parsed.get("summary", "")[:512],
        payload=parsed.get("payload") or {},
        status="open",
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    # Proactive contact: the assistant reaches out on its own here rather than only reacting to
    # a request - the second such event besides an expired timer (see scheduler.py). Best-effort
    # and never allowed to fail the suggestion itself (which is already committed above).
    try:
        user = await db.get(User, notification.user_id)
        if user is not None:
            await push_service.send_push(db, user, title="Neuer Vorschlag", body=suggestion.summary)
    except Exception:  # noqa: BLE001 - a failed push must never undo/fail an already-saved suggestion
        logger.exception("Failed to send push for suggestion %s", suggestion.id)

    return suggestion

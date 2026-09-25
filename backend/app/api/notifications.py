from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_device_by_api_key
from app.db.models import Device, NotificationRaw, NotificationSuggestion, User
from app.db.session import async_session_maker, get_db
from app.errors import NotFound
from app.schemas.notifications import (
    NotificationIngestRequest,
    NotificationIngestResponse,
    SuggestionOut,
    SuggestionsListOut,
    SuggestionStatusOut,
)
from app.services import calendar_service, notification_service
from app.utils import parse_iso_datetime

router = APIRouter(tags=["notifications"])


async def _classify_in_background(notification_id: str) -> None:
    async with async_session_maker() as db:
        notification = await db.get(NotificationRaw, notification_id)
        if notification is not None:
            await notification_service.classify_and_create_suggestion(db, notification)


@router.post("/notifications/ingest", response_model=NotificationIngestResponse, status_code=202)
async def ingest_notification(
    payload: NotificationIngestRequest,
    background_tasks: BackgroundTasks,
    device: Device = Depends(get_device_by_api_key),
    db: AsyncSession = Depends(get_db),
) -> NotificationIngestResponse:
    notification = await notification_service.ingest(db, device, payload)
    background_tasks.add_task(_classify_in_background, notification.id)
    return NotificationIngestResponse(notification_id=notification.id)


@router.get("/notifications/suggestions", response_model=SuggestionsListOut)
async def list_suggestions(
    status: str = "open",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestionsListOut:
    query = select(NotificationSuggestion).where(NotificationSuggestion.user_id == user.id)
    if status:
        query = query.where(NotificationSuggestion.status == status)
    result = await db.execute(query.order_by(NotificationSuggestion.created_at.desc()))
    return SuggestionsListOut(suggestions=list(result.scalars().all()))


async def _get_owned_suggestion(db: AsyncSession, user: User, suggestion_id: str) -> NotificationSuggestion:
    suggestion = await db.get(NotificationSuggestion, suggestion_id)
    if suggestion is None or suggestion.user_id != user.id:
        raise NotFound("Vorschlag nicht gefunden.")
    return suggestion


@router.post("/notifications/suggestions/{suggestion_id}/apply", response_model=SuggestionOut)
async def apply_suggestion(
    suggestion_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSuggestion:
    suggestion = await _get_owned_suggestion(db, user, suggestion_id)

    if suggestion.kind == "calendar_event":
        payload = suggestion.payload
        start = parse_iso_datetime(payload["start"])
        end = parse_iso_datetime(payload["end"]) if payload.get("end") else start
        await calendar_service.create_event(
            db,
            user,
            title=payload.get("title", suggestion.summary),
            start=start,
            end=end,
            location=payload.get("location"),
        )

    suggestion.status = "applied"
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.post("/notifications/suggestions/{suggestion_id}/dismiss", response_model=SuggestionStatusOut)
async def dismiss_suggestion(
    suggestion_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestionStatusOut:
    suggestion = await _get_owned_suggestion(db, user, suggestion_id)
    suggestion.status = "dismissed"
    await db.commit()
    return SuggestionStatusOut(status="dismissed")

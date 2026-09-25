from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.calendar import (
    CalDAVConnectRequest,
    CalDAVConnectResponse,
    EventCreateRequest,
    EventOut,
    EventsListOut,
)
from app.services import calendar_service

router = APIRouter(tags=["calendar"])


@router.post("/integrations/caldav", response_model=CalDAVConnectResponse)
async def connect_caldav(
    payload: CalDAVConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalDAVConnectResponse:
    await calendar_service.connect(db, user, payload.url, payload.username, payload.password)
    return CalDAVConnectResponse()


@router.get("/calendar/events", response_model=EventsListOut)
async def list_events(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventsListOut:
    range_start = start or datetime.now(timezone.utc)
    range_end = end or (range_start + timedelta(days=14))
    events = await calendar_service.list_events(db, user, range_start, range_end)
    return EventsListOut(events=[EventOut(**e) for e in events])


@router.post("/calendar/events", response_model=EventOut, status_code=201)
async def create_event(
    payload: EventCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventOut:
    event = await calendar_service.create_event(
        db, user, title=payload.title, start=payload.start, end=payload.end, location=payload.location
    )
    return EventOut(**event)

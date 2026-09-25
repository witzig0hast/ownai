from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import UtcDatetime


class CalDAVConnectRequest(BaseModel):
    url: str
    username: str
    password: str


class CalDAVConnectResponse(BaseModel):
    connected: bool = True


class EventOut(BaseModel):
    id: str
    title: str
    start: UtcDatetime
    end: UtcDatetime
    location: str | None = None
    source: str = "caldav"


class EventsListOut(BaseModel):
    events: list[EventOut]


class EventCreateRequest(BaseModel):
    title: str
    start: datetime
    end: datetime
    location: str | None = None

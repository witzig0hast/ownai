from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class NotificationIngestRequest(BaseModel):
    package_name: str
    app_label: str
    title: str
    text: str
    posted_at: datetime
    category: Literal["msg", "sms", "other"] = "other"


class NotificationIngestResponse(BaseModel):
    accepted: bool = True
    notification_id: str


class SuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notification_id: str
    kind: Literal["calendar_event", "reply_draft"]
    summary: str
    payload: dict[str, Any]
    status: Literal["open", "applied", "dismissed"]
    created_at: UtcDatetime


class SuggestionsListOut(BaseModel):
    suggestions: list[SuggestionOut]


class SuggestionStatusOut(BaseModel):
    status: str

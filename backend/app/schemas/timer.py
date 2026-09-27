from pydantic import BaseModel

from app.schemas.common import UtcDatetime


class TimerOut(BaseModel):
    id: str
    label: str | None
    ends_at: UtcDatetime


class TimersListOut(BaseModel):
    timers: list[TimerOut]

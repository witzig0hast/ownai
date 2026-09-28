from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UtcDatetime

Recurrence = Literal["daily", "weekly", "monthly"]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class ReminderCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    recurrence: Recurrence
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    weekday: Weekday | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def _fields_match_recurrence(self) -> "ReminderCreateRequest":
        if self.recurrence == "weekly" and self.weekday is None:
            raise ValueError("weekday ist bei recurrence='weekly' erforderlich.")
        if self.recurrence == "monthly" and self.day_of_month is None:
            raise ValueError("day_of_month ist bei recurrence='monthly' erforderlich.")
        return self


class ReminderUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    recurrence: Recurrence | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    weekday: Weekday | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    active: bool | None = None


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    recurrence: Recurrence
    hour: int
    minute: int
    weekday: Weekday | None
    day_of_month: int | None
    active: bool
    created_at: UtcDatetime


class RemindersListOut(BaseModel):
    reminders: list[ReminderOut]

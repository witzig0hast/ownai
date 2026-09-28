from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime


class AutomationCreateRequest(BaseModel):
    entity_id: str = Field(min_length=1, max_length=255)
    trigger_state: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=255)


class AutomationUpdateRequest(BaseModel):
    entity_id: str | None = Field(default=None, min_length=1, max_length=255)
    trigger_state: str | None = Field(default=None, min_length=1, max_length=255)
    message: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None


class AutomationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_id: str
    trigger_state: str
    message: str
    active: bool
    last_seen_state: str | None
    created_at: UtcDatetime


class AutomationsListOut(BaseModel):
    automations: list[AutomationOut]

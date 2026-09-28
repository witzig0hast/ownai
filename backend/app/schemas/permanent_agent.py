from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime

MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 60 * 24 * 7  # one week


class PermanentAgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    preset: str
    role_prompt: str = Field(min_length=1, max_length=2000)
    interval_minutes: int = Field(ge=MIN_INTERVAL_MINUTES, le=MAX_INTERVAL_MINUTES)


class PermanentAgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role_prompt: str | None = Field(default=None, min_length=1, max_length=2000)
    interval_minutes: int | None = Field(default=None, ge=MIN_INTERVAL_MINUTES, le=MAX_INTERVAL_MINUTES)
    active: bool | None = None


class PermanentAgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    preset: str
    role_prompt: str
    interval_minutes: int
    active: bool
    last_run_at: UtcDatetime | None
    created_at: UtcDatetime


class PermanentAgentsListOut(BaseModel):
    agents: list[PermanentAgentOut]


class AgentLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    notable: bool
    created_at: UtcDatetime


class AgentLogEntriesListOut(BaseModel):
    entries: list[AgentLogEntryOut]


class AgentPresetOut(BaseModel):
    key: str
    name: str
    description: str


class AgentPresetsListOut(BaseModel):
    presets: list[AgentPresetOut]

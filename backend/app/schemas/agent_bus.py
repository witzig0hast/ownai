from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UtcDatetime


class AgentIdentityCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class AgentIdentityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: UtcDatetime


class AgentIdentityCreateResponse(AgentIdentityOut):
    api_key: str


class AgentIdentitiesListOut(BaseModel):
    agents: list[AgentIdentityOut]


class AgentMessageSendRequest(BaseModel):
    """`to` is an agent's name, or the reserved value "ownai" for the account owner
    themself - see app/services/agent_bus_service.py. Exactly one of content (kind="text") or
    task_type (kind="task") must be set, matching `kind`."""

    to: str = Field(min_length=1, max_length=64)
    kind: Literal["text", "task"]
    content: str | None = Field(default=None, max_length=10000)
    task_type: str | None = Field(default=None, max_length=64)
    payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check_kind_fields(self) -> "AgentMessageSendRequest":
        if self.kind == "text" and not self.content:
            raise ValueError("content ist bei kind='text' erforderlich.")
        if self.kind == "task" and not self.task_type:
            raise ValueError("task_type ist bei kind='task' erforderlich.")
        return self


class AgentMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    from_label: str
    to_label: str
    kind: Literal["text", "task"]
    content: str | None
    task_type: str | None
    payload: dict[str, Any] | None
    status: Literal["sent", "pending", "in_progress", "completed", "failed"]
    result: dict[str, Any] | None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class AgentMessagesListOut(BaseModel):
    messages: list[AgentMessageOut]


class AgentMessageResultRequest(BaseModel):
    status: Literal["completed", "failed"]
    result: dict[str, Any] | None = None

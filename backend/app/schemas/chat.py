from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None
    archived: bool
    skill: str
    updated_at: UtcDatetime


class ConversationsListOut(BaseModel):
    conversations: list[ConversationOut]


class ConversationCreateRequest(BaseModel):
    title: str | None = None


class ConversationUpdateRequest(BaseModel):
    """Partial update - only fields that are set change. `title` can't be cleared back to null
    this way (min_length=1); a conversation only ever loses its title by being deleted."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    archived: bool | None = None
    skill: str | None = None


class SkillOut(BaseModel):
    key: str
    name: str
    description: str


class SkillsListOut(BaseModel):
    skills: list[SkillOut]


class ToolCallOut(BaseModel):
    tool: str
    arguments: dict[str, Any]
    result: Any


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCallOut] | None = None
    created_at: UtcDatetime


class MessagesListOut(BaseModel):
    messages: list[MessageOut]


class MessageCreateRequest(BaseModel):
    content: str


class MessageCreateResponse(BaseModel):
    message: MessageOut

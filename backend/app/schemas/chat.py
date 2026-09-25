from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None
    updated_at: UtcDatetime


class ConversationsListOut(BaseModel):
    conversations: list[ConversationOut]


class ConversationCreateRequest(BaseModel):
    title: str | None = None


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

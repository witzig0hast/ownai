from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class PendingActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    tool_name: str
    summary: str
    status: str
    created_at: UtcDatetime


class PendingActionsListOut(BaseModel):
    pending_actions: list[PendingActionOut]

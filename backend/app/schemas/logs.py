from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class LogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    level: str
    message: str
    detail: str | None
    created_at: UtcDatetime


class LogsListOut(BaseModel):
    logs: list[LogEntryOut]
    categories: list[str]

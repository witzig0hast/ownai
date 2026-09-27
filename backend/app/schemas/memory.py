from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime


class MemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=512)


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    created_at: UtcDatetime


class MemoriesListOut(BaseModel):
    memories: list[MemoryOut]

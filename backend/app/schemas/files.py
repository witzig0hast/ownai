from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class GeneratedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime_type: str
    size_bytes: int
    created_at: UtcDatetime


class GeneratedFilesListOut(BaseModel):
    files: list[GeneratedFileOut]

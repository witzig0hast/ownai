from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime

ListKind = Literal["todo", "shopping"]


class ListItemCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=512)


class ListItemUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=512)
    done: bool | None = None


class ListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    done: bool
    created_at: UtcDatetime


class ListCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: ListKind


class ListUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class ListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: ListKind
    created_at: UtcDatetime
    items: list[ListItemOut]


class ListsListOut(BaseModel):
    lists: list[ListOut]

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime


class RssFeedCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1024)
    name: str | None = Field(default=None, max_length=255)


class RssFeedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    name: str | None
    created_at: UtcDatetime


class RssFeedsListOut(BaseModel):
    feeds: list[RssFeedOut]


class RssItemOut(BaseModel):
    feed_name: str
    title: str
    link: str
    published: str | None
    summary: str | None


class RssItemsListOut(BaseModel):
    items: list[RssItemOut]

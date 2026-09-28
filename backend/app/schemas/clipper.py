from pydantic import BaseModel, Field


class ClipRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class ClipOut(BaseModel):
    title: str
    url: str
    text: str

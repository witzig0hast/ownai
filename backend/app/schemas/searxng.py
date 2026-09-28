from pydantic import BaseModel


class SearxngConnectRequest(BaseModel):
    url: str


class SearxngConnectResponse(BaseModel):
    connected: bool = True


class SearxngStatusOut(BaseModel):
    connected: bool
    url: str | None


class SearchResultOut(BaseModel):
    title: str
    url: str
    content: str | None


class SearchResultsOut(BaseModel):
    results: list[SearchResultOut]

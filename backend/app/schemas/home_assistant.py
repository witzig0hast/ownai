from pydantic import BaseModel


class HomeAssistantConnectRequest(BaseModel):
    url: str
    token: str


class HomeAssistantConnectResponse(BaseModel):
    connected: bool = True


class HomeAssistantEntityOut(BaseModel):
    entity_id: str
    domain: str
    state: str | None
    friendly_name: str


class HomeAssistantEntitiesListOut(BaseModel):
    entities: list[HomeAssistantEntityOut]

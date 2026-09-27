from pydantic import BaseModel


class VapidPublicKeyOut(BaseModel):
    public_key: str | None
    configured: bool


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    """Mirrors the shape of the browser's PushSubscription.toJSON() output."""

    endpoint: str
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str

from typing import Literal

from pydantic import BaseModel


class DeviceRegisterRequest(BaseModel):
    platform: Literal["android", "ios", "web"]
    push_token: str | None = None
    label: str


class DeviceOut(BaseModel):
    id: str
    platform: str
    device_api_key: str
    label: str

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class DeviceRegisterRequest(BaseModel):
    platform: Literal["android", "ios", "web"]
    push_token: str | None = None
    label: str


class DeviceOut(BaseModel):
    id: str
    platform: str
    device_api_key: str
    label: str


class DeviceListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    label: str
    created_at: UtcDatetime


class DevicesListOut(BaseModel):
    devices: list[DeviceListItemOut]

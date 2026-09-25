from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import TokenError, decode_token, hash_device_api_key
from app.db.models import Device, User
from app.db.session import get_db
from app.errors import InvalidDeviceKey, NotAuthenticated


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NotAuthenticated()
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise NotAuthenticated(str(exc)) from exc

    user = await db.get(User, payload["sub"])
    if user is None:
        raise NotAuthenticated()
    return user


async def get_device_by_api_key(
    x_device_key: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> Device:
    if not x_device_key:
        raise InvalidDeviceKey("X-Device-Key Header fehlt.")
    key_hash = hash_device_api_key(x_device_key)
    result = await db.execute(select(Device).where(Device.api_key_hash == key_hash))
    device = result.scalar_one_or_none()
    if device is None:
        raise InvalidDeviceKey()
    return device

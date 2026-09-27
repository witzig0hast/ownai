from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import TokenError, decode_token, hash_device_api_key
from app.db.models import Device, User
from app.db.session import get_db
from app.errors import InvalidDeviceKey, NotAdmin, NotAuthenticated, SystemPaused
from app.services import admin_service


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


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise NotAdmin()
    return user


async def require_not_paused(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    """Gate for the actual LLM/resource-heavy endpoints (chat messages) only - never applied to
    auth, or the admin endpoints themselves, so a paused system can always still be unpaused."""
    settings = await admin_service.get_settings(db)
    if settings.system_paused:
        raise SystemPaused(settings.system_paused_message or "Das System ist aktuell pausiert.")
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

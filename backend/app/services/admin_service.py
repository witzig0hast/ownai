from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSettings, User

SETTINGS_ID = "singleton"


async def get_settings(db: AsyncSession) -> AppSettings:
    settings = await db.get(AppSettings, SETTINGS_ID)
    if settings is None:
        settings = AppSettings(id=SETTINGS_ID)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_settings(
    db: AsyncSession,
    *,
    registration_open: bool | None = None,
    system_paused: bool | None = None,
    system_paused_message: str | None = None,
) -> AppSettings:
    settings = await get_settings(db)
    if registration_open is not None:
        settings.registration_open = registration_open
    if system_paused is not None:
        settings.system_paused = system_paused
    if system_paused_message is not None:
        settings.system_paused_message = system_paused_message or None
    await db.commit()
    await db.refresh(settings)
    return settings


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def user_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()

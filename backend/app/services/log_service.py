from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppLog, User

MAX_RESULTS = 200


async def log(
    db: AsyncSession,
    *,
    category: str,
    message: str,
    user: User | None = None,
    level: str = "info",
    detail: str | None = None,
) -> AppLog:
    """Records one entry, visible to the user via GET /logs (Settings -> Logs tab). Commits
    immediately (independent of whatever transaction the caller is in) so a log entry about a
    failure survives even if the caller's own transaction then rolls back."""
    entry = AppLog(
        user_id=user.id if user else None,
        category=category,
        level=level,
        message=message,
        detail=detail,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_logs(
    db: AsyncSession,
    user: User,
    *,
    category: str | None = None,
    level: str | None = None,
    q: str | None = None,
) -> list[AppLog]:
    """Only the calling user's own entries (plus any category-less system entries) - this is a
    Settings-tab feature, not an admin audit log."""
    stmt = select(AppLog).where((AppLog.user_id == user.id) | (AppLog.user_id.is_(None)))
    if category:
        stmt = stmt.where(AppLog.category == category)
    if level:
        stmt = stmt.where(AppLog.level == level)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(AppLog.message.ilike(like) | AppLog.detail.ilike(like))
    stmt = stmt.order_by(AppLog.created_at.desc()).limit(MAX_RESULTS)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_categories(db: AsyncSession, user: User) -> list[str]:
    """Distinct categories the user actually has entries for, so the frontend's filter dropdown
    only ever shows options that return something."""
    stmt = (
        select(AppLog.category)
        .where((AppLog.user_id == user.id) | (AppLog.user_id.is_(None)))
        .distinct()
        .order_by(AppLog.category)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.logs import LogsListOut
from app.services import log_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=LogsListOut)
async def list_logs(
    category: str | None = Query(default=None),
    level: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LogsListOut:
    logs = await log_service.list_logs(db, user, category=category, level=level, q=q)
    categories = await log_service.list_categories(db, user)
    return LogsListOut(logs=logs, categories=categories)

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.services import search_service

router = APIRouter(tags=["search"])


@router.get("/search/all")
async def search(
    q: str = Query(min_length=2, max_length=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    return {"results": await search_service.search(db, user, q)}

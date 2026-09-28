from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.searxng import (
    SearchResultsOut,
    SearxngConnectRequest,
    SearxngConnectResponse,
    SearxngStatusOut,
)
from app.services import searxng_service

router = APIRouter(tags=["searxng"])


@router.post("/integrations/searxng", response_model=SearxngConnectResponse)
async def connect_searxng(
    payload: SearxngConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearxngConnectResponse:
    await searxng_service.connect(db, user, payload.url)
    return SearxngConnectResponse()


@router.get("/integrations/searxng", response_model=SearxngStatusOut)
async def searxng_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearxngStatusOut:
    account = await searxng_service.get_account(db, user)
    return SearxngStatusOut(connected=account is not None, url=account.url if account else None)


@router.get("/search", response_model=SearchResultsOut)
async def web_search(
    q: str = Query(min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResultsOut:
    results = await searxng_service.search(db, user, q)
    return SearchResultsOut(results=results)

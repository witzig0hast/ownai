from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.rss import RssFeedCreateRequest, RssFeedOut, RssFeedsListOut, RssItemsListOut
from app.services import rss_service

router = APIRouter(prefix="/rss", tags=["rss"])


@router.post("/feeds", response_model=RssFeedOut, status_code=201)
async def create_feed(
    payload: RssFeedCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RssFeedOut:
    return await rss_service.add_feed(db, user, payload.url, payload.name)


@router.get("/feeds", response_model=RssFeedsListOut)
async def list_feeds(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> RssFeedsListOut:
    feeds = await rss_service.list_feeds(db, user)
    return RssFeedsListOut(feeds=feeds)


@router.delete("/feeds/{feed_id}", status_code=204)
async def delete_feed(
    feed_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await rss_service.delete_feed(db, user, feed_id)


@router.get("/items", response_model=RssItemsListOut)
async def list_items(
    feed_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RssItemsListOut:
    items = await rss_service.latest_items(db, user, feed_id)
    return RssItemsListOut(items=items)

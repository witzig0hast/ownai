from typing import Any

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RssFeed, User
from app.errors import APIError

MAX_ITEMS_PER_FEED = 10
MAX_SUMMARY_LENGTH = 500


class RssFeedNotFound(APIError):
    def __init__(self, message: str = "Feed nicht gefunden."):
        super().__init__(404, "not_found", message)


class RssFeedError(APIError):
    def __init__(self, message: str):
        super().__init__(502, "rss_feed_error", message)


def _client() -> httpx.AsyncClient:
    """Separate factory purely so tests can monkeypatch it - same pattern as
    home_assistant_service._client / weather_service._client / searxng_service._client."""
    return httpx.AsyncClient(timeout=15.0, follow_redirects=True)


async def _fetch_parsed(url: str) -> feedparser.FeedParserDict:
    async with _client() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RssFeedError(f"Feed nicht erreichbar: {exc}") from exc

    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise RssFeedError(f"Konnte den Feed nicht lesen: {parsed.get('bozo_exception')}")
    return parsed


async def add_feed(db: AsyncSession, user: User, url: str, name: str | None) -> RssFeed:
    if not name:
        parsed = await _fetch_parsed(url)
        name = parsed.feed.get("title") or url

    feed = RssFeed(user_id=user.id, url=url, name=name)
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return feed


async def list_feeds(db: AsyncSession, user: User) -> list[RssFeed]:
    result = await db.execute(select(RssFeed).where(RssFeed.user_id == user.id).order_by(RssFeed.created_at))
    return list(result.scalars().all())


async def delete_feed(db: AsyncSession, user: User, feed_id: str) -> None:
    feed = await db.get(RssFeed, feed_id)
    if feed is None or feed.user_id != user.id:
        raise RssFeedNotFound()
    await db.delete(feed)
    await db.commit()


def _entry_to_item(feed_name: str, entry: Any) -> dict:
    summary = entry.get("summary")
    if summary and len(summary) > MAX_SUMMARY_LENGTH:
        summary = summary[:MAX_SUMMARY_LENGTH] + "…"
    return {
        "feed_name": feed_name,
        "title": entry.get("title", "(ohne Titel)"),
        "link": entry.get("link", ""),
        "published": entry.get("published") or entry.get("updated"),
        "summary": summary,
    }


async def latest_items(db: AsyncSession, user: User, feed_id: str | None = None) -> list[dict]:
    if feed_id is not None:
        feed = await db.get(RssFeed, feed_id)
        if feed is None or feed.user_id != user.id:
            raise RssFeedNotFound()
        feeds = [feed]
    else:
        feeds = await list_feeds(db, user)

    items: list[dict] = []
    for feed in feeds:
        parsed = await _fetch_parsed(feed.url)
        feed_name = feed.name or feed.url
        items.extend(_entry_to_item(feed_name, entry) for entry in parsed.entries[:MAX_ITEMS_PER_FEED])
    return items

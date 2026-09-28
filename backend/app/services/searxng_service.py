from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SearxngAccount, User
from app.errors import APIError

MAX_RESULTS = 8


class SearxngNotConnected(APIError):
    def __init__(self, message: str = "Keine SearXNG-Instanz verbunden."):
        super().__init__(409, "searxng_not_connected", message)


class SearxngError(APIError):
    def __init__(self, message: str):
        super().__init__(502, "searxng_error", message)


async def get_account(db: AsyncSession, user: User) -> SearxngAccount | None:
    result = await db.execute(select(SearxngAccount).where(SearxngAccount.user_id == user.id))
    return result.scalar_one_or_none()


async def connect(db: AsyncSession, user: User, url: str) -> SearxngAccount:
    url = url.rstrip("/")
    existing = await get_account(db, user)
    if existing is not None:
        existing.url = url
        account = existing
    else:
        account = SearxngAccount(user_id=user.id, url=url)
        db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


def _client() -> httpx.AsyncClient:
    """Separate factory purely so tests can monkeypatch it - same pattern as
    home_assistant_service._client / weather_service._client."""
    return httpx.AsyncClient(timeout=15.0)


async def search(db: AsyncSession, user: User, query: str) -> list[dict[str, Any]]:
    account = await get_account(db, user)
    if account is None:
        raise SearxngNotConnected()

    async with _client() as client:
        try:
            response = await client.get(
                f"{account.url}/search", params={"q": query, "format": "json"}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearxngError(f"SearXNG nicht erreichbar: {exc}") from exc

    try:
        results = response.json()["results"]
    except (KeyError, ValueError) as exc:
        raise SearxngError("SearXNG hat kein gültiges JSON zurückgegeben - ist format=json aktiviert?") from exc

    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content")}
        for r in results[:MAX_RESULTS]
    ]

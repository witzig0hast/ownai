from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HomeAssistantAccount, User
from app.errors import APIError
from app.services.crypto import decrypt, encrypt

# Only entity domains a personal assistant should be able to act on. Deliberately excludes
# administrative/scripting domains (homeassistant.*, shell_command, python_script, ...) that
# HA's service-call API would otherwise let a tool call reach - this is a safety boundary,
# not a completeness list; extend it if you use a domain that's missing.
ALLOWED_DOMAINS = {
    "light",
    "switch",
    "climate",
    "cover",
    "fan",
    "lock",
    "media_player",
    "scene",
    "script",
    "vacuum",
    "humidifier",
    "water_heater",
    "input_boolean",
}


class HomeAssistantNotConnected(APIError):
    def __init__(self, message: str = "Kein Home Assistant verbunden."):
        super().__init__(409, "home_assistant_not_connected", message)


class HomeAssistantError(APIError):
    def __init__(self, message: str):
        super().__init__(502, "home_assistant_error", message)


async def get_account(db: AsyncSession, user: User) -> HomeAssistantAccount | None:
    result = await db.execute(select(HomeAssistantAccount).where(HomeAssistantAccount.user_id == user.id))
    return result.scalar_one_or_none()


async def connect(db: AsyncSession, user: User, url: str, token: str) -> HomeAssistantAccount:
    url = url.rstrip("/")
    existing = await get_account(db, user)
    if existing is not None:
        existing.url = url
        existing.encrypted_token = encrypt(token)
        account = existing
    else:
        account = HomeAssistantAccount(user_id=user.id, url=url, encrypted_token=encrypt(token))
        db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


def _client(account: HomeAssistantAccount) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=account.url,
        headers={
            "Authorization": f"Bearer {decrypt(account.encrypted_token)}",
            "Content-Type": "application/json",
        },
        timeout=15.0,
    )


async def _require_account(db: AsyncSession, user: User) -> HomeAssistantAccount:
    account = await get_account(db, user)
    if account is None:
        raise HomeAssistantNotConnected()
    return account


async def list_entities(db: AsyncSession, user: User, domain: str | None = None) -> list[dict[str, Any]]:
    account = await _require_account(db, user)
    async with _client(account) as client:
        try:
            response = await client.get("/api/states")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HomeAssistantError(f"Home Assistant nicht erreichbar: {exc}") from exc

    states = response.json()
    results = []
    for state in states:
        entity_id = state.get("entity_id", "")
        entity_domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain and entity_domain != domain:
            continue
        results.append(
            {
                "entity_id": entity_id,
                "domain": entity_domain,
                "state": state.get("state"),
                "friendly_name": state.get("attributes", {}).get("friendly_name", entity_id),
            }
        )
    return results


async def call_service(
    db: AsyncSession, user: User, entity_id: str, service: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    if "." not in entity_id:
        raise HomeAssistantError(f"Ungültige entity_id: {entity_id!r}")
    domain = entity_id.split(".", 1)[0]
    if domain not in ALLOWED_DOMAINS:
        raise HomeAssistantError(
            f"Domain {domain!r} ist nicht erlaubt. Erlaubt: {', '.join(sorted(ALLOWED_DOMAINS))}."
        )

    account = await _require_account(db, user)
    payload = {"entity_id": entity_id, **(data or {})}
    async with _client(account) as client:
        try:
            response = await client.post(f"/api/services/{domain}/{service}", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HomeAssistantError(f"Home Assistant hat den Befehl abgelehnt: {exc}") from exc

    return {"entity_id": entity_id, "service": service, "ok": True}

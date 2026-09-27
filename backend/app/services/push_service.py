import asyncio
import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import PushSubscription, User

logger = logging.getLogger(__name__)


def is_push_configured() -> bool:
    settings = get_settings()
    return bool(settings.vapid_public_key and settings.vapid_private_key)


async def add_subscription(
    db: AsyncSession, user: User, *, endpoint: str, p256dh: str, auth: str
) -> PushSubscription:
    existing = await db.execute(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    record = existing.scalar_one_or_none()
    if record is not None:
        record.user_id = user.id
        record.p256dh = p256dh
        record.auth = auth
    else:
        record = PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def remove_subscription(db: AsyncSession, user: User, endpoint: str) -> None:
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == endpoint, PushSubscription.user_id == user.id
        )
    )
    await db.commit()


def _send_sync(subscription: PushSubscription, payload: dict) -> int | None:
    """Returns the HTTP status code of a failed send (so the caller can decide whether the
    subscription is gone and should be dropped), or None on success."""
    settings = get_settings()
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        logger.warning("Push send failed (endpoint=%s, status=%s): %s", subscription.endpoint, status, exc)
        return status
    return None


async def send_push(db: AsyncSession, user: User, *, title: str, body: str, url: str | None = None) -> None:
    """Sends a Web Push notification to every browser/device the user has subscribed on.
    Best-effort per subscription: a single failed send never raises - an expired/gone
    subscription (410/404) is dropped, anything else is just logged. If push isn't configured
    at all (no VAPID keys) or the user has no subscriptions, this is a silent no-op."""
    if not is_push_configured():
        return

    result = await db.execute(select(PushSubscription).where(PushSubscription.user_id == user.id))
    subscriptions = list(result.scalars().all())
    if not subscriptions:
        return

    payload = {"title": title, "body": body, "url": url}
    stale_ids: list[str] = []
    for subscription in subscriptions:
        status = await asyncio.to_thread(_send_sync, subscription, payload)
        if status in (404, 410):
            stale_ids.append(subscription.id)

    if stale_ids:
        await db.execute(delete(PushSubscription).where(PushSubscription.id.in_(stale_ids)))
        await db.commit()

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Timer, User
from app.db.session import async_session_maker
from app.services import push_service, scheduler


async def test_expired_timer_triggers_push_once(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/timer", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    pushed = []
    monkeypatch.setattr(
        push_service,
        "_send_sync",
        lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None,
    )

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        timer = Timer(
            user_id=user.id,
            label="Nudeln",
            ends_at=datetime.now(timezone.utc) - timedelta(seconds=5),
        )
        db.add(timer)
        await db.commit()
        timer_id = timer.id

    await scheduler._check_expired_timers()

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/timer"
    assert payload["title"] == "Timer abgelaufen"
    assert payload["body"] == "Nudeln"

    async with async_session_maker() as db:
        refreshed = await db.get(Timer, timer_id)
        assert refreshed.notified is True

    # Running the poll again must not re-notify an already-notified timer.
    await scheduler._check_expired_timers()
    assert len(pushed) == 1


async def test_cancelled_timer_is_never_notified(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    pushed = []
    monkeypatch.setattr(
        push_service, "_send_sync", lambda subscription, payload: pushed.append(subscription.endpoint) or None
    )

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        timer = Timer(
            user_id=user.id,
            label="Abgebrochen",
            ends_at=datetime.now(timezone.utc) - timedelta(seconds=5),
            cancelled=True,
        )
        db.add(timer)
        await db.commit()

    await scheduler._check_expired_timers()
    assert pushed == []

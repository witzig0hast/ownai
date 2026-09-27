import json

from httpx import AsyncClient

from app.config import get_settings
from app.services import ollama_client, push_service


async def test_vapid_public_key_unconfigured_by_default(client: AsyncClient, auth_headers: dict):
    response = await client.get("/push/vapid-public-key", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"public_key": None, "configured": False}


async def test_vapid_public_key_reflects_config(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    response = await client.get("/push/vapid-public-key", headers=auth_headers)
    assert response.json() == {"public_key": "pub-key", "configured": True}


async def test_subscribe_then_unsubscribe(client: AsyncClient, auth_headers: dict):
    subscribed = await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/abc", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )
    assert subscribed.status_code == 204

    # Re-subscribing the same endpoint updates rather than duplicates (upsert by endpoint).
    resubscribed = await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/abc", "keys": {"p256dh": "p2", "auth": "a2"}},
        headers=auth_headers,
    )
    assert resubscribed.status_code == 204

    unsubscribed = await client.post(
        "/push/unsubscribe", json={"endpoint": "https://push.example/abc"}, headers=auth_headers
    )
    assert unsubscribed.status_code == 204


async def test_send_push_is_noop_when_unconfigured(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(push_service, "_send_sync", lambda *a, **k: calls.__setitem__("n", calls["n"] + 1))

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/xyz", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    from app.db.models import User
    from app.db.session import async_session_maker
    from sqlalchemy import select

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        await push_service.send_push(db, user, title="Hi", body="Test")

    assert calls["n"] == 0  # never sent - no VAPID keys configured


async def test_send_push_sends_to_all_subscriptions_and_drops_stale_ones(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/alive", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )
    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/gone", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    sent_to = []

    def fake_send_sync(subscription, payload):  # noqa: ARG001
        sent_to.append(subscription.endpoint)
        return 410 if subscription.endpoint.endswith("gone") else None

    monkeypatch.setattr(push_service, "_send_sync", fake_send_sync)

    from app.db.models import PushSubscription, User
    from app.db.session import async_session_maker
    from sqlalchemy import select

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        await push_service.send_push(db, user, title="Hi", body="Test")

        remaining = (await db.execute(select(PushSubscription))).scalars().all()

    assert set(sent_to) == {"https://push.example/alive", "https://push.example/gone"}
    assert [s.endpoint for s in remaining] == ["https://push.example/alive"]


async def test_new_suggestion_sends_proactive_push(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/for-suggestion", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    pushed = []
    monkeypatch.setattr(
        push_service,
        "_send_sync",
        lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None,
    )

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {
            "role": "assistant",
            "content": json.dumps(
                {
                    "relevant": True,
                    "kind": "calendar_event",
                    "summary": "Termin erkannt: heute 19 Uhr",
                    "payload": {"title": "X", "start": "2026-09-25T19:00:00Z", "end": "2026-09-25T20:00:00Z"},
                }
            ),
        }

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    device_registered = await client.post(
        "/devices/register",
        json={"platform": "android", "label": "S25 Ultra", "push_token": None},
        headers=auth_headers,
    )
    device_key = device_registered.json()["device_api_key"]

    await client.post(
        "/notifications/ingest",
        json={
            "package_name": "com.whatsapp",
            "app_label": "WhatsApp",
            "title": "Anna",
            "text": "Bist du heute um 19 Uhr da?",
            "posted_at": "2026-09-25T18:02:00Z",
            "category": "msg",
        },
        headers={"X-Device-Key": device_key},
    )

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/for-suggestion"
    assert payload["title"] == "Neuer Vorschlag"
    assert "Termin erkannt" in payload["body"]

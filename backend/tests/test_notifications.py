import json

from httpx import AsyncClient

from app.services import ollama_client


async def _register_device(client: AsyncClient, auth_headers: dict) -> str:
    response = await client.post(
        "/devices/register",
        json={"platform": "android", "label": "S25 Ultra", "push_token": None},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["device_api_key"]


async def test_ingest_requires_device_key(client: AsyncClient):
    response = await client.post(
        "/notifications/ingest",
        json={
            "package_name": "com.whatsapp",
            "app_label": "WhatsApp",
            "title": "Anna",
            "text": "Bist du heute um 19 Uhr da?",
            "posted_at": "2026-09-25T18:02:00Z",
            "category": "msg",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_device_key"


async def test_relevant_notification_produces_suggestion(client: AsyncClient, auth_headers: dict, monkeypatch):
    device_key = await _register_device(client, auth_headers)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        classification = {
            "relevant": True,
            "kind": "calendar_event",
            "summary": "Termin erkannt: heute 19 Uhr mit Anna",
            "payload": {"title": "Anna", "start": "2026-09-25T19:00:00Z", "end": "2026-09-25T20:00:00Z"},
        }
        return {"role": "assistant", "content": json.dumps(classification)}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    ingested = await client.post(
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
    assert ingested.status_code == 202

    suggestions = await client.get("/notifications/suggestions", headers=auth_headers)
    assert suggestions.status_code == 200
    items = suggestions.json()["suggestions"]
    assert len(items) == 1
    assert items[0]["kind"] == "calendar_event"
    assert items[0]["status"] == "open"


async def test_irrelevant_notification_produces_no_suggestion(client: AsyncClient, auth_headers: dict, monkeypatch):
    device_key = await _register_device(client, auth_headers)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": json.dumps({"relevant": False, "kind": None, "payload": {}})}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await client.post(
        "/notifications/ingest",
        json={
            "package_name": "com.example.ads",
            "app_label": "Ads",
            "title": "50% Rabatt!",
            "text": "Nur heute: alles reduziert",
            "posted_at": "2026-09-25T18:02:00Z",
            "category": "other",
        },
        headers={"X-Device-Key": device_key},
    )

    suggestions = await client.get("/notifications/suggestions", headers=auth_headers)
    assert suggestions.json()["suggestions"] == []


async def test_dismiss_suggestion(client: AsyncClient, auth_headers: dict, monkeypatch):
    device_key = await _register_device(client, auth_headers)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        classification = {"relevant": True, "kind": "reply_draft", "summary": "Antwort vorschlagen", "payload": {"reply": "Ja, bin da!"}}
        return {"role": "assistant", "content": json.dumps(classification)}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await client.post(
        "/notifications/ingest",
        json={
            "package_name": "com.whatsapp",
            "app_label": "WhatsApp",
            "title": "Anna",
            "text": "Bist du da?",
            "posted_at": "2026-09-25T18:02:00Z",
            "category": "msg",
        },
        headers={"X-Device-Key": device_key},
    )

    suggestions = await client.get("/notifications/suggestions", headers=auth_headers)
    suggestion_id = suggestions.json()["suggestions"][0]["id"]

    dismissed = await client.post(f"/notifications/suggestions/{suggestion_id}/dismiss", headers=auth_headers)
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"

    open_suggestions = await client.get("/notifications/suggestions?status=open", headers=auth_headers)
    assert open_suggestions.json()["suggestions"] == []

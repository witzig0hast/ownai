from httpx import AsyncClient

from app.services import email_service, ollama_client
from tests.conftest import drain_background_tasks


async def test_logs_empty_by_default(client: AsyncClient, auth_headers: dict):
    response = await client.get("/logs", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"logs": [], "categories": []}


async def test_failed_send_email_is_logged_and_filterable(client: AsyncClient, auth_headers: dict, monkeypatch):
    await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )

    def fake_send_sync(config, to, subject, body):  # noqa: ARG001
        raise email_service._SendPhaseError("login", OSError("bad credentials"))

    monkeypatch.setattr(email_service, "_send_sync", fake_send_sync)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "send_email",
                            "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hi"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Ging nicht.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine Test-Mail"},
        headers=auth_headers,
    )
    await drain_background_tasks()

    all_logs = await client.get("/logs", headers=auth_headers)
    assert all_logs.status_code == 200
    body = all_logs.json()
    assert body["categories"] == ["email"]
    assert len(body["logs"]) == 1
    entry = body["logs"][0]
    assert entry["category"] == "email"
    assert entry["level"] == "error"
    assert "Anmeldung" in entry["message"]
    assert "bad credentials" in entry["detail"]

    filtered = await client.get("/logs?category=email", headers=auth_headers)
    assert len(filtered.json()["logs"]) == 1

    wrong_category = await client.get("/logs?category=calendar", headers=auth_headers)
    assert wrong_category.json()["logs"] == []

    searched = await client.get("/logs?q=credentials", headers=auth_headers)
    assert len(searched.json()["logs"]) == 1

    no_match = await client.get("/logs?q=nonexistent-xyz", headers=auth_headers)
    assert no_match.json()["logs"] == []


async def test_successful_send_email_is_logged_as_info(client: AsyncClient, auth_headers: dict, monkeypatch):
    await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )
    monkeypatch.setattr(email_service, "_send_sync", lambda *a, **k: None)  # noqa: ARG005

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "send_email",
                            "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hi"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine Test-Mail"},
        headers=auth_headers,
    )
    await drain_background_tasks()

    logs = await client.get("/logs?level=info", headers=auth_headers)
    entries = logs.json()["logs"]
    assert len(entries) == 1
    assert entries[0]["level"] == "info"
    assert "erfolgreich gesendet" in entries[0]["message"]


async def test_logs_requires_auth(client: AsyncClient):
    response = await client.get("/logs")
    assert response.status_code == 401

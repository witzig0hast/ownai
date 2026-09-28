from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.db.models import PermanentAgent, User
from app.db.session import async_session_maker
from app.services import ollama_client, permanent_agent_service, push_service


async def test_list_presets(client: AsyncClient, auth_headers: dict):
    response = await client.get("/permanent-agents/presets", headers=auth_headers)
    assert response.status_code == 200
    keys = {p["key"] for p in response.json()["presets"]}
    assert "web_watcher" in keys
    assert "weather_watcher" in keys


async def test_create_list_update_delete_agent(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/permanent-agents",
        json={
            "name": "Krypto-Beobachter",
            "preset": "web_watcher",
            "role_prompt": "Beobachte den Bitcoin-Kurs.",
            "interval_minutes": 60,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    agent = created.json()
    assert agent["name"] == "Krypto-Beobachter"
    assert agent["active"] is True
    assert agent["last_run_at"] is None
    agent_id = agent["id"]

    listed = await client.get("/permanent-agents", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["agents"]) == 1

    updated = await client.patch(f"/permanent-agents/{agent_id}", json={"active": False}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    deleted = await client.delete(f"/permanent-agents/{agent_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed_again = await client.get("/permanent-agents", headers=auth_headers)
    assert listed_again.json()["agents"] == []


async def test_create_agent_with_invalid_preset_is_422(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/permanent-agents",
        json={"name": "X", "preset": "not_a_real_preset", "role_prompt": "Test", "interval_minutes": 60},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_interval_below_minimum_is_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/permanent-agents",
        json={"name": "X", "preset": "web_watcher", "role_prompt": "Test", "interval_minutes": 1},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_delete_foreign_agent_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/permanent-agents/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_log_starts_empty(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/permanent-agents",
        json={"name": "X", "preset": "weather_watcher", "role_prompt": "Test", "interval_minutes": 60},
        headers=auth_headers,
    )
    agent_id = created.json()["id"]

    log = await client.get(f"/permanent-agents/{agent_id}/log", headers=auth_headers)
    assert log.status_code == 200
    assert log.json()["entries"] == []


async def test_run_agent_once_records_log_and_updates_last_run(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    created = await client.post(
        "/permanent-agents",
        json={"name": "Wetter-Test", "preset": "weather_watcher", "role_prompt": "Test", "interval_minutes": 60},
        headers=auth_headers,
    )
    agent_id = created.json()["id"]

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        return {"role": "assistant", "content": "Alles ruhig, keine Änderungen.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    async with async_session_maker() as db:
        agent = await db.get(PermanentAgent, agent_id)
        user = (await db.execute(select(User))).scalar_one()
        assert agent.last_run_at is None
        entry = await permanent_agent_service.run_agent_once(db, user, agent)
        assert entry.content == "Alles ruhig, keine Änderungen."
        assert entry.notable is False

    log = await client.get(f"/permanent-agents/{agent_id}/log", headers=auth_headers)
    entries = log.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["content"] == "Alles ruhig, keine Änderungen."

    refreshed = await client.get("/permanent-agents", headers=auth_headers)
    assert refreshed.json()["agents"][0]["last_run_at"] is not None


async def test_flag_finding_marks_notable_and_sends_push(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings_response = await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/agent", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )
    assert settings_response.status_code == 204

    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    pushed = []
    monkeypatch.setattr(
        push_service, "_send_sync", lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None
    )

    created = await client.post(
        "/permanent-agents",
        json={"name": "Krypto-Beobachter", "preset": "web_watcher", "role_prompt": "Test", "interval_minutes": 60},
        headers=auth_headers,
    )
    agent_id = created.json()["id"]

    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "flag_finding", "arguments": {"message": "Bitcoin +10% heute!"}}}
                ],
            }
        return {"role": "assistant", "content": "Fertig.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    async with async_session_maker() as db:
        agent = await db.get(PermanentAgent, agent_id)
        user = (await db.execute(select(User))).scalar_one()
        entry = await permanent_agent_service.run_agent_once(db, user, agent)
        assert entry.notable is True
        assert "Bitcoin +10%" in entry.content

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/agent"
    assert payload["title"] == "Krypto-Beobachter"


async def test_run_agent_once_handles_ollama_unreachable(client: AsyncClient, auth_headers: dict, monkeypatch):
    created = await client.post(
        "/permanent-agents",
        json={"name": "X", "preset": "weather_watcher", "role_prompt": "Test", "interval_minutes": 60},
        headers=auth_headers,
    )
    agent_id = created.json()["id"]

    async def failing_chat(messages, tools=None):  # noqa: ARG001
        raise ollama_client.OllamaError("connection refused")

    monkeypatch.setattr(ollama_client, "chat", failing_chat)

    async with async_session_maker() as db:
        agent = await db.get(PermanentAgent, agent_id)
        user = (await db.execute(select(User))).scalar_one()
        entry = await permanent_agent_service.run_agent_once(db, user, agent)
        assert "Ollama nicht erreichbar" in entry.content
        assert agent.last_run_at is not None  # still marked as run, so it doesn't retry every poll


async def test_chat_tool_creates_agent(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "create_permanent_agent",
                            "arguments": {
                                "name": "Krypto-Beobachter",
                                "preset": "web_watcher",
                                "role_prompt": "Beobachte den Bitcoin-Kurs",
                                "interval_minutes": 60,
                            },
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Erledigt.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Leg mir einen Agenten an, der den Bitcoin-Kurs beobachtet"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["name"] == "Krypto-Beobachter"

    listed = await client.get("/permanent-agents", headers=auth_headers)
    assert listed.json()["agents"][0]["name"] == "Krypto-Beobachter"

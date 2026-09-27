from httpx import AsyncClient

from app.config import get_settings
from app.services import ollama_client, push_service


async def _register_agent(client: AsyncClient, auth_headers: dict, name: str, description: str | None = None) -> dict:
    response = await client.post(
        "/agent-bus/agents", json={"name": name, "description": description}, headers=auth_headers
    )
    assert response.status_code == 201
    return response.json()


async def test_register_and_list_agents(client: AsyncClient, auth_headers: dict):
    created = await _register_agent(client, auth_headers, "shop-backend", "Mein Shop-Projekt")
    assert created["name"] == "shop-backend"
    assert created["api_key"].startswith("ownai_ak_")

    listed = await client.get("/agent-bus/agents", headers=auth_headers)
    assert listed.status_code == 200
    agents = listed.json()["agents"]
    assert len(agents) == 1
    assert agents[0]["name"] == "shop-backend"
    assert "api_key" not in agents[0]


async def test_duplicate_agent_name_rejected(client: AsyncClient, auth_headers: dict):
    await _register_agent(client, auth_headers, "shop-backend")
    response = await client.post("/agent-bus/agents", json={"name": "shop-backend"}, headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "agent_name_taken"


async def test_reserved_name_ownai_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.post("/agent-bus/agents", json={"name": "ownai"}, headers=auth_headers)
    assert response.status_code == 409


async def test_delete_agent(client: AsyncClient, auth_headers: dict):
    created = await _register_agent(client, auth_headers, "shop-backend")
    deleted = await client.delete(f"/agent-bus/agents/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 204

    listed = await client.get("/agent-bus/agents", headers=auth_headers)
    assert listed.json()["agents"] == []


async def test_agent_sends_text_message_to_ownai_and_user_sees_it(client: AsyncClient, auth_headers: dict):
    created = await _register_agent(client, auth_headers, "shop-backend")
    agent_key = created["api_key"]

    sent = await client.post(
        "/agent-bus/messages",
        json={"to": "ownai", "kind": "text", "content": "Neue Bestellung eingegangen"},
        headers={"X-Agent-Key": agent_key},
    )
    assert sent.status_code == 201
    body = sent.json()
    assert body["from_label"] == "shop-backend"
    assert body["to_label"] == "ownai"
    assert body["status"] == "sent"

    listed = await client.get("/agent-bus/messages", headers=auth_headers)
    messages = listed.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "Neue Bestellung eingegangen"


async def test_user_sends_task_to_agent_and_agent_sees_it_in_inbox(client: AsyncClient, auth_headers: dict):
    created = await _register_agent(client, auth_headers, "shop-backend")
    agent_key = created["api_key"]

    sent = await client.post(
        "/agent-bus/messages",
        json={"to": "shop-backend", "kind": "task", "task_type": "sync_inventory", "payload": {"sku": "ABC"}},
        headers=auth_headers,
    )
    assert sent.status_code == 201
    assert sent.json()["status"] == "pending"
    message_id = sent.json()["id"]

    inbox = await client.get("/agent-bus/inbox", headers={"X-Agent-Key": agent_key})
    assert inbox.status_code == 200
    inbox_messages = inbox.json()["messages"]
    assert len(inbox_messages) == 1
    assert inbox_messages[0]["task_type"] == "sync_inventory"
    assert inbox_messages[0]["payload"] == {"sku": "ABC"}

    result = await client.post(
        f"/agent-bus/messages/{message_id}/result",
        json={"status": "completed", "result": {"updated": 3}},
        headers={"X-Agent-Key": agent_key},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert result.json()["result"] == {"updated": 3}


async def test_message_to_unknown_agent_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/agent-bus/messages",
        json={"to": "does-not-exist", "kind": "text", "content": "Hi"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "agent_not_found"


async def test_invalid_agent_key_is_rejected(client: AsyncClient):
    response = await client.get("/agent-bus/inbox", headers={"X-Agent-Key": "not-a-real-key"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_agent_key"


async def test_agent_cannot_submit_result_for_message_addressed_to_another_agent(
    client: AsyncClient, auth_headers: dict
):
    await _register_agent(client, auth_headers, "agent-a")
    agent_b = await _register_agent(client, auth_headers, "agent-b")

    sent = await client.post(
        "/agent-bus/messages",
        json={"to": "agent-a", "kind": "task", "task_type": "do_thing"},
        headers=auth_headers,
    )
    message_id = sent.json()["id"]

    forbidden = await client.post(
        f"/agent-bus/messages/{message_id}/result",
        json={"status": "completed", "result": {}},
        headers={"X-Agent-Key": agent_b["api_key"]},
    )
    assert forbidden.status_code == 404


async def test_message_to_ownai_triggers_push(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/bus", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    pushed = []
    monkeypatch.setattr(
        push_service,
        "_send_sync",
        lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None,
    )

    created = await _register_agent(client, auth_headers, "shop-backend")
    await client.post(
        "/agent-bus/messages",
        json={"to": "ownai", "kind": "text", "content": "Wichtiges Ereignis"},
        headers={"X-Agent-Key": created["api_key"]},
    )

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/bus"
    assert "shop-backend" in payload["title"]


async def test_chat_tool_sends_agent_bus_message(client: AsyncClient, auth_headers: dict, monkeypatch):
    await _register_agent(client, auth_headers, "shop-backend")

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
                            "name": "agent_bus_send_message",
                            "arguments": {"to": "shop-backend", "kind": "text", "content": "Status?"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Nachricht gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    conversation = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = conversation.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Frag meinen Shop-Agent nach dem Status"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["to"] == "shop-backend"
    assert result["status"] == "sent"

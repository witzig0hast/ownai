import httpx
import pytest
from httpx import AsyncClient

from app.services import home_assistant_service

FAKE_STATES = [
    {
        "entity_id": "light.wohnzimmer",
        "state": "off",
        "attributes": {"friendly_name": "Wohnzimmerlicht"},
    },
    {
        "entity_id": "switch.kaffeemaschine",
        "state": "on",
        "attributes": {"friendly_name": "Kaffeemaschine"},
    },
    {
        "entity_id": "sensor.temperatur",
        "state": "21.5",
        "attributes": {"friendly_name": "Temperatur"},
    },
]


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/states" and request.method == "GET":
        return httpx.Response(200, json=FAKE_STATES)
    if request.url.path == "/api/services/light/turn_on" and request.method == "POST":
        return httpx.Response(200, json=[{"entity_id": "light.wohnzimmer", "state": "on"}])
    if request.url.path == "/api/services/homeassistant/restart":
        return httpx.Response(200, json=[])
    return httpx.Response(404, json={"message": "not found"})


@pytest.fixture(autouse=True)
def _patch_ha_client(monkeypatch):
    def fake_client(account):
        return httpx.AsyncClient(
            base_url=account.url,
            transport=httpx.MockTransport(_mock_handler),
        )

    monkeypatch.setattr(home_assistant_service, "_client", fake_client)


async def test_entities_require_connected_home_assistant(client: AsyncClient, auth_headers: dict):
    response = await client.get("/home-assistant/entities", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "home_assistant_not_connected"


async def test_connect_then_list_entities(client: AsyncClient, auth_headers: dict):
    connect = await client.post(
        "/integrations/home-assistant",
        json={"url": "http://homeassistant.local:8123", "token": "secret-token"},
        headers=auth_headers,
    )
    assert connect.status_code == 200
    assert connect.json() == {"connected": True}

    listed = await client.get("/home-assistant/entities", headers=auth_headers)
    assert listed.status_code == 200
    entities = listed.json()["entities"]
    assert len(entities) == 3
    assert entities[0] == {
        "entity_id": "light.wohnzimmer",
        "domain": "light",
        "state": "off",
        "friendly_name": "Wohnzimmerlicht",
    }


async def test_list_entities_filters_by_domain(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/integrations/home-assistant",
        json={"url": "http://homeassistant.local:8123", "token": "secret-token"},
        headers=auth_headers,
    )
    listed = await client.get("/home-assistant/entities?domain=switch", headers=auth_headers)
    entities = listed.json()["entities"]
    assert len(entities) == 1
    assert entities[0]["entity_id"] == "switch.kaffeemaschine"


async def test_call_service_turns_on_light(client: AsyncClient, auth_headers: dict, monkeypatch):
    from app.services import ollama_client

    await client.post(
        "/integrations/home-assistant",
        json={"url": "http://homeassistant.local:8123", "token": "secret-token"},
        headers=auth_headers,
    )

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
                            "name": "home_assistant_call_service",
                            "arguments": {"entity_id": "light.wohnzimmer", "service": "turn_on"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Licht ist an.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Mach das Wohnzimmerlicht an"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    message = sent.json()["message"]
    assert message["content"] == "Licht ist an."
    assert message["tool_calls"] == [
        {
            "tool": "home_assistant_call_service",
            "arguments": {"entity_id": "light.wohnzimmer", "service": "turn_on"},
            "result": {"entity_id": "light.wohnzimmer", "service": "turn_on", "ok": True},
        }
    ]


async def test_call_service_rejects_disallowed_domain(client: AsyncClient, auth_headers: dict, monkeypatch):
    from app.services import ollama_client

    await client.post(
        "/integrations/home-assistant",
        json={"url": "http://homeassistant.local:8123", "token": "secret-token"},
        headers=auth_headers,
    )

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
                            "name": "home_assistant_call_service",
                            "arguments": {"entity_id": "homeassistant.restart", "service": "restart"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Das darf ich nicht.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Starte Home Assistant neu"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    message = sent.json()["message"]
    result = message["tool_calls"][0]["result"]
    assert "nicht erlaubt" in result["error"]

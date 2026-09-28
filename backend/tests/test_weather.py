import httpx
import pytest
from httpx import AsyncClient

from app.services import ollama_client, weather_service

GEOCODING_RESPONSE = {
    "results": [{"name": "Berlin", "country": "Germany", "latitude": 52.52, "longitude": 13.405}]
}

FORECAST_RESPONSE = {
    "current": {"temperature_2m": 18.5, "weather_code": 3, "wind_speed_10m": 12.0},
    "daily": {
        "time": ["2026-09-28", "2026-09-29", "2026-09-30"],
        "temperature_2m_max": [20.0, 21.0, 19.5],
        "temperature_2m_min": [12.0, 13.0, 11.0],
        "weather_code": [3, 61, 0],
    },
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "geocoding-api.open-meteo.com":
        if request.url.params.get("name") == "Nirgendwo":
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json=GEOCODING_RESPONSE)
    if request.url.host == "api.open-meteo.com":
        return httpx.Response(200, json=FORECAST_RESPONSE)
    return httpx.Response(404, json={"message": "not found"})


@pytest.fixture(autouse=True)
def _patch_weather_client(monkeypatch):
    monkeypatch.setattr(
        weather_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
    )


async def test_get_weather_for_known_location(client: AsyncClient, auth_headers: dict):
    response = await client.get("/weather?location=Berlin", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Berlin"
    assert body["country"] == "Germany"
    assert body["current_temperature"] == 18.5
    assert body["current_condition"] == "Bedeckt"
    assert len(body["daily"]) == 3
    assert body["daily"][1]["condition"] == "Leichter Regen"


async def test_get_weather_for_unknown_location_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.get("/weather?location=Nirgendwo", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "location_not_found"


async def test_get_weather_requires_auth(client: AsyncClient):
    response = await client.get("/weather?location=Berlin")
    assert response.status_code == 401


async def test_chat_tool_gets_weather(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "get_weather", "arguments": {"location": "Berlin"}}}],
            }
        return {"role": "assistant", "content": "18.5 Grad.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Wie ist das Wetter in Berlin?"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["current_temperature"] == 18.5

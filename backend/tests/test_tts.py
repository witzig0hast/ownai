import httpx
import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.services import tts_service

FAKE_MP3_BYTES = b"\xff\xfb\x90\x00fake-mp3-audio"


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/audio/speech":
        return httpx.Response(200, content=FAKE_MP3_BYTES, headers={"content-type": "audio/mpeg"})
    if request.url.path == "/v1/audio/voices":
        return httpx.Response(200, json={"voices": ["martin"]})
    return httpx.Response(404, json={"message": "not found"})


@pytest.fixture(autouse=True)
def _patch_tts_client(monkeypatch):
    monkeypatch.setattr(
        tts_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
    )


@pytest.fixture
def _configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "kokoro_tts_base_url", "http://kokoro.invalid")


async def test_voices_empty_when_not_configured(client: AsyncClient, auth_headers: dict):
    response = await client.get("/tts/voices", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["voices"] == []


async def test_speak_returns_not_configured_error(client: AsyncClient, auth_headers: dict):
    response = await client.post("/tts/speak", json={"text": "Hallo"}, headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "tts_not_configured"


async def test_voices_lists_configured_server(client: AsyncClient, auth_headers: dict, _configured):
    response = await client.get("/tts/voices", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["voices"] == ["martin"]


async def test_speak_returns_audio_when_configured(client: AsyncClient, auth_headers: dict, _configured):
    response = await client.post("/tts/speak", json={"text": "Hallo Welt"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == FAKE_MP3_BYTES


async def test_speak_empty_text_returns_no_content(client: AsyncClient, auth_headers: dict, _configured):
    response = await client.post("/tts/speak", json={"text": "   "}, headers=auth_headers)
    assert response.status_code == 204


async def test_speak_requires_auth(client: AsyncClient):
    response = await client.post("/tts/speak", json={"text": "Hallo"})
    assert response.status_code == 401


async def test_speak_surfaces_unreachable_server(client: AsyncClient, auth_headers: dict, monkeypatch, _configured):
    def _raise(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(tts_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_raise)))

    response = await client.post("/tts/speak", json={"text": "Hallo"}, headers=auth_headers)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "tts_unavailable"

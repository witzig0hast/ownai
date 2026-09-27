from httpx import AsyncClient

from app.services import whisper_client


async def test_transcribe_requires_auth(client: AsyncClient):
    response = await client.post(
        "/voice/transcribe", files={"audio": ("clip.webm", b"fake-bytes", "audio/webm")}
    )
    assert response.status_code == 401


async def test_transcribe_returns_text(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_transcribe(audio_bytes: bytes, language: str | None = None) -> str:
        assert audio_bytes == b"fake-bytes"
        return "wie ist das wetter heute"

    monkeypatch.setattr(whisper_client, "transcribe", fake_transcribe)

    response = await client.post(
        "/voice/transcribe",
        files={"audio": ("clip.webm", b"fake-bytes", "audio/webm")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"text": "wie ist das wetter heute"}


async def test_transcribe_rejects_empty_audio(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/voice/transcribe",
        files={"audio": ("clip.webm", b"", "audio/webm")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_audio"


async def test_transcribe_surfaces_whisper_error(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def failing_transcribe(audio_bytes: bytes, language: str | None = None) -> str:
        raise whisper_client.WhisperError("Whisper-Server nicht erreichbar: connection refused")

    monkeypatch.setattr(whisper_client, "transcribe", failing_transcribe)

    response = await client.post(
        "/voice/transcribe",
        files={"audio": ("clip.webm", b"fake-bytes", "audio/webm")},
        headers=auth_headers,
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "whisper_unavailable"

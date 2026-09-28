import httpx

from app.config import get_settings


class TTSError(Exception):
    pass


def is_configured() -> bool:
    return bool(get_settings().kokoro_tts_base_url)


def _client() -> httpx.AsyncClient:
    """Separate factory (rather than inlining httpx.AsyncClient() calls) purely so tests can
    monkeypatch it - same pattern as weather_service._client."""
    return httpx.AsyncClient(timeout=30.0)


def _parse_voices(data: object) -> list[str]:
    """Defensive about the exact response shape - OpenAI-compatible TTS servers vary between
    a bare list of voice ids, {"voices": [...]}, and a list of {"id"/"name": ...} objects."""
    raw = data.get("voices", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    voices: list[str] = []
    for entry in raw:
        if isinstance(entry, str):
            voices.append(entry)
        elif isinstance(entry, dict):
            voice_id = entry.get("id") or entry.get("name")
            if voice_id:
                voices.append(str(voice_id))
    return voices


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """Calls the configured OpenAI-compatible TTS server's /v1/audio/speech endpoint and
    returns the raw audio bytes (mp3)."""
    settings = get_settings()
    if not settings.kokoro_tts_base_url:
        raise TTSError("Kein TTS-Server konfiguriert (KOKORO_TTS_BASE_URL).")

    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice or settings.kokoro_tts_voice,
        "response_format": "mp3",
    }
    base_url = settings.kokoro_tts_base_url.rstrip("/")
    async with _client() as client:
        try:
            response = await client.post(f"{base_url}/v1/audio/speech", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TTSError(f"TTS-Server nicht erreichbar: {exc}") from exc
    return response.content


async def list_voices() -> list[str]:
    settings = get_settings()
    if not settings.kokoro_tts_base_url:
        return []

    base_url = settings.kokoro_tts_base_url.rstrip("/")
    async with _client() as client:
        try:
            response = await client.get(f"{base_url}/v1/audio/voices")
            response.raise_for_status()
        except httpx.HTTPError:
            return []
    return _parse_voices(response.json())

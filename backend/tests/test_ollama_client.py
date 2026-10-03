import json

import httpx
import pytest

from app.config import get_settings
from app.services import ollama_client


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-1", -1),
        ("0", 0),
        ("42", 42),
        ("30m", "30m"),
        ("1h", "1h"),
    ],
)
def test_keep_alive_payload_value_converts_plain_integers_only(raw, expected):
    assert ollama_client._keep_alive_payload_value(raw) == expected


async def test_chat_sends_keep_alive_as_a_real_number_not_a_quoted_string(monkeypatch):
    """Regression test: OLLAMA_KEEP_ALIVE=-1 (our documented default for a dedicated GPU, see
    .env.example) previously got JSON-encoded as the STRING "-1" in the request body. Ollama
    parses a string keep_alive with Go's time.ParseDuration, which rejects a bare "-1" (no unit
    suffix) and returns 400 Bad Request for the entire /api/chat call - breaking every single
    chat/voice message, not just a slow one. The payload must carry a real JSON number instead."""
    get_settings.cache_clear()
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "-1")
    get_settings.cache_clear()

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Hi", "tool_calls": []}})

    original_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    await ollama_client.chat([{"role": "user", "content": "Hi"}])

    assert captured["body"]["keep_alive"] == -1
    # The crux of the bug: must be a JSON number, never a string, however it compares equal.
    assert not isinstance(captured["body"]["keep_alive"], str)

    get_settings.cache_clear()

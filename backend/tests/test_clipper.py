import httpx
import pytest
from httpx import AsyncClient

from app.services import clipper_service, ollama_client

SAMPLE_HTML = b"""<!DOCTYPE html>
<html>
<head><title>Beispielartikel</title></head>
<body>
  <nav>Navigation-Links hier</nav>
  <script>console.log("sollte nicht im Text landen");</script>
  <style>body { color: red; }</style>
  <header>Kopfzeile</header>
  <article>
    <h1>Beispielartikel</h1>
    <p>Das ist der eigentliche Artikeltext, den wir extrahieren wollen.</p>
  </article>
  <footer>Fusszeile</footer>
</body>
</html>
"""


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if str(request.url) == "https://example.com/article":
        return httpx.Response(200, content=SAMPLE_HTML, headers={"content-type": "text/html; charset=utf-8"})
    if str(request.url) == "https://example.com/empty":
        return httpx.Response(200, content=b"<html><body></body></html>", headers={"content-type": "text/html"})
    return httpx.Response(404, text="not found")


@pytest.fixture(autouse=True)
def _patch_clipper_client(monkeypatch):
    monkeypatch.setattr(
        clipper_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
    )


async def test_clip_extracts_title_and_strips_noise(client: AsyncClient, auth_headers: dict):
    response = await client.post("/clip", json={"url": "https://example.com/article"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Beispielartikel"
    assert "eigentliche Artikeltext" in body["text"]
    assert "sollte nicht im Text landen" not in body["text"]
    assert "Navigation-Links" not in body["text"]
    assert "Kopfzeile" not in body["text"]
    assert "Fusszeile" not in body["text"]


async def test_clip_empty_page_errors(client: AsyncClient, auth_headers: dict):
    response = await client.post("/clip", json={"url": "https://example.com/empty"}, headers=auth_headers)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "clip_error"


async def test_clip_unreachable_page_errors(client: AsyncClient, auth_headers: dict):
    response = await client.post("/clip", json={"url": "https://example.com/missing"}, headers=auth_headers)
    assert response.status_code == 502


async def test_chat_tool_clip_url(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "clip_url", "arguments": {"url": "https://example.com/article"}}}],
            }
        return {"role": "assistant", "content": "Zusammenfassung: ...", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Fasse https://example.com/article zusammen"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["title"] == "Beispielartikel"


async def test_chat_tool_save_clipped_page(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "save_clipped_page", "arguments": {"url": "https://example.com/article"}}}
                ],
            }
        return {"role": "assistant", "content": "Gespeichert.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Speichere https://example.com/article"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["filename"] == "Beispielartikel.md"
    assert "download_url" in result

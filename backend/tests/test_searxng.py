import httpx
import pytest
from httpx import AsyncClient

from app.services import ollama_client, searxng_service

FAKE_RESULTS = {
    "results": [
        {"title": "OwnAI GitHub", "url": "https://github.com/example/ownai", "content": "Ein privater KI-Assistent."},
        {"title": "Zweiter Treffer", "url": "https://example.com/2", "content": "Noch ein Treffer."},
    ]
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search" and request.url.params.get("format") == "json":
        return httpx.Response(200, json=FAKE_RESULTS)
    return httpx.Response(404, json={"message": "not found"})


@pytest.fixture(autouse=True)
def _patch_searxng_client(monkeypatch):
    monkeypatch.setattr(
        searxng_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
    )


async def test_search_requires_connected_searxng(client: AsyncClient, auth_headers: dict):
    response = await client.get("/search?q=ownai", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "searxng_not_connected"


async def test_status_before_and_after_connect(client: AsyncClient, auth_headers: dict):
    before = await client.get("/integrations/searxng", headers=auth_headers)
    assert before.json() == {"connected": False, "url": None}

    await client.post("/integrations/searxng", json={"url": "http://searxng.local:8080/"}, headers=auth_headers)

    after = await client.get("/integrations/searxng", headers=auth_headers)
    assert after.json() == {"connected": True, "url": "http://searxng.local:8080"}


async def test_connect_then_search(client: AsyncClient, auth_headers: dict):
    connected = await client.post(
        "/integrations/searxng", json={"url": "http://searxng.local:8080"}, headers=auth_headers
    )
    assert connected.status_code == 200
    assert connected.json() == {"connected": True}

    searched = await client.get("/search?q=ownai", headers=auth_headers)
    assert searched.status_code == 200
    results = searched.json()["results"]
    assert len(results) == 2
    assert results[0] == {
        "title": "OwnAI GitHub",
        "url": "https://github.com/example/ownai",
        "content": "Ein privater KI-Assistent.",
    }


async def test_chat_tool_web_search(client: AsyncClient, auth_headers: dict, monkeypatch):
    await client.post("/integrations/searxng", json={"url": "http://searxng.local:8080"}, headers=auth_headers)

    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "web_search", "arguments": {"query": "ownai"}}}],
            }
        return {"role": "assistant", "content": "Hier ist was ich gefunden habe.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Suche im Web nach ownai"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert len(result) == 2
    assert result[0]["title"] == "OwnAI GitHub"

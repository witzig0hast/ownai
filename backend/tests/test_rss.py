import httpx
import pytest
from httpx import AsyncClient

from app.services import ollama_client, rss_service

FEED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OwnAI Blog</title>
    <link>https://example.com</link>
    <description>News about OwnAI</description>
    <item>
      <title>Erster Artikel</title>
      <link>https://example.com/1</link>
      <description>Zusammenfassung des ersten Artikels.</description>
      <pubDate>Mon, 28 Sep 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Zweiter Artikel</title>
      <link>https://example.com/2</link>
      <description>Zusammenfassung des zweiten Artikels.</description>
      <pubDate>Sun, 27 Sep 2026 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if str(request.url) == "https://example.com/feed.xml":
        return httpx.Response(200, content=FEED_XML, headers={"content-type": "application/rss+xml"})
    return httpx.Response(404, text="not found")


@pytest.fixture(autouse=True)
def _patch_rss_client(monkeypatch):
    monkeypatch.setattr(
        rss_service, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
    )


async def test_add_feed_without_name_uses_feed_title(client: AsyncClient, auth_headers: dict):
    created = await client.post("/rss/feeds", json={"url": "https://example.com/feed.xml"}, headers=auth_headers)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "OwnAI Blog"
    assert body["url"] == "https://example.com/feed.xml"


async def test_add_feed_with_explicit_name(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/rss/feeds", json={"url": "https://example.com/feed.xml", "name": "Mein Feed"}, headers=auth_headers
    )
    assert created.json()["name"] == "Mein Feed"


async def test_list_and_delete_feed(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/rss/feeds", json={"url": "https://example.com/feed.xml", "name": "Blog"}, headers=auth_headers
    )
    feed_id = created.json()["id"]

    listed = await client.get("/rss/feeds", headers=auth_headers)
    assert len(listed.json()["feeds"]) == 1

    deleted = await client.delete(f"/rss/feeds/{feed_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed_again = await client.get("/rss/feeds", headers=auth_headers)
    assert listed_again.json()["feeds"] == []


async def test_delete_foreign_feed_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/rss/feeds/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_list_items_from_feed(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/rss/feeds", json={"url": "https://example.com/feed.xml", "name": "Blog"}, headers=auth_headers
    )
    feed_id = created.json()["id"]

    items = await client.get(f"/rss/items?feed_id={feed_id}", headers=auth_headers)
    assert items.status_code == 200
    body = items.json()["items"]
    assert len(body) == 2
    assert body[0]["title"] == "Erster Artikel"
    assert body[0]["feed_name"] == "Blog"
    assert body[0]["link"] == "https://example.com/1"


async def test_list_items_without_feed_id_covers_all_feeds(client: AsyncClient, auth_headers: dict):
    await client.post("/rss/feeds", json={"url": "https://example.com/feed.xml", "name": "Blog"}, headers=auth_headers)

    items = await client.get("/rss/items", headers=auth_headers)
    assert len(items.json()["items"]) == 2


async def test_chat_tool_adds_feed(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "add_rss_feed", "arguments": {"url": "https://example.com/feed.xml"}}}
                ],
            }
        return {"role": "assistant", "content": "Abonniert.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Abonniere https://example.com/feed.xml"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["name"] == "OwnAI Blog"

from httpx import AsyncClient

from app.services import ollama_client


async def test_create_list_and_read_back(client: AsyncClient, auth_headers: dict):
    created = await client.post("/lists", json={"name": "Einkaufsliste", "kind": "shopping"}, headers=auth_headers)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Einkaufsliste"
    assert body["kind"] == "shopping"
    assert body["items"] == []

    listed = await client.get("/lists", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["lists"]) == 1
    assert listed.json()["lists"][0]["items"] == []


async def test_rename_and_delete_list(client: AsyncClient, auth_headers: dict):
    created = await client.post("/lists", json={"name": "Todo", "kind": "todo"}, headers=auth_headers)
    list_id = created.json()["id"]

    renamed = await client.patch(f"/lists/{list_id}", json={"name": "Wochenende"}, headers=auth_headers)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Wochenende"

    deleted = await client.delete(f"/lists/{list_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed = await client.get("/lists", headers=auth_headers)
    assert listed.json()["lists"] == []


async def test_delete_foreign_list_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/lists/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_add_toggle_and_delete_item(client: AsyncClient, auth_headers: dict):
    created = await client.post("/lists", json={"name": "Einkaufsliste", "kind": "shopping"}, headers=auth_headers)
    list_id = created.json()["id"]

    added = await client.post(f"/lists/{list_id}/items", json={"content": "Milch"}, headers=auth_headers)
    assert added.status_code == 201
    body = added.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["content"] == "Milch"
    assert body["items"][0]["done"] is False
    item_id = body["items"][0]["id"]

    added2 = await client.post(f"/lists/{list_id}/items", json={"content": "Brot"}, headers=auth_headers)
    assert len(added2.json()["items"]) == 2

    toggled = await client.patch(f"/lists/{list_id}/items/{item_id}", json={"done": True}, headers=auth_headers)
    assert toggled.status_code == 200
    milch_item = next(i for i in toggled.json()["items"] if i["id"] == item_id)
    assert milch_item["done"] is True

    deleted = await client.delete(f"/lists/{list_id}/items/{item_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert len(deleted.json()["items"]) == 1
    assert deleted.json()["items"][0]["content"] == "Brot"


async def test_item_on_foreign_list_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/lists/does-not-exist/items", json={"content": "Milch"}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_chat_tool_creates_list_and_adds_item(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "create_list", "arguments": {"name": "Einkaufsliste", "kind": "shopping"}}}
                ],
            }
        return {"role": "assistant", "content": "Erledigt.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Leg mir eine Einkaufsliste an"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["name"] == "Einkaufsliste"

    listed = await client.get("/lists", headers=auth_headers)
    assert listed.json()["lists"][0]["name"] == "Einkaufsliste"

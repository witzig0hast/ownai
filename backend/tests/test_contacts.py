from httpx import AsyncClient

from app.services import ollama_client


async def test_create_list_update_delete_contact(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/contacts",
        json={"name": "Anna Muster", "phone": "+49123", "birthday_month": 5, "birthday_day": 17},
        headers=auth_headers,
    )
    assert created.status_code == 201
    contact = created.json()
    assert contact["name"] == "Anna Muster"
    assert contact["birthday_month"] == 5
    assert contact["birthday_day"] == 17
    contact_id = contact["id"]

    listed = await client.get("/contacts", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["contacts"]) == 1

    updated = await client.patch(f"/contacts/{contact_id}", json={"phone": "+49999"}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+49999"
    assert updated.json()["name"] == "Anna Muster"  # untouched fields survive a partial update

    deleted = await client.delete(f"/contacts/{contact_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed_again = await client.get("/contacts", headers=auth_headers)
    assert listed_again.json()["contacts"] == []


async def test_delete_foreign_contact_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/contacts/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_birthday_month_requires_day(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/contacts", json={"name": "Halbe Angabe", "birthday_month": 5}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_chat_tool_adds_and_removes_contact(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "add_contact", "arguments": {"name": "Max Mustermann"}}}],
            }
        return {"role": "assistant", "content": "Gespeichert.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Merk dir Max Mustermann als Kontakt"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["name"] == "Max Mustermann"

    listed = await client.get("/contacts", headers=auth_headers)
    assert listed.json()["contacts"][0]["name"] == "Max Mustermann"

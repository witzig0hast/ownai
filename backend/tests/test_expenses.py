from httpx import AsyncClient

from app.services import ollama_client


async def test_create_and_list_expense(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/expenses",
        json={"amount": 12.5, "description": "Mittagessen", "category": "Essen"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["amount"] == 12.5
    assert body["category"] == "Essen"
    assert body["spent_at"]  # defaulted to today

    listed = await client.get("/expenses", headers=auth_headers)
    assert listed.status_code == 200
    data = listed.json()
    assert len(data["expenses"]) == 1
    assert data["total"] == 12.5
    assert data["by_category"] == {"Essen": 12.5}


async def test_uncategorized_expense_grouped_under_sonstiges(client: AsyncClient, auth_headers: dict):
    await client.post("/expenses", json={"amount": 5.0, "description": "Kaffee"}, headers=auth_headers)

    listed = await client.get("/expenses", headers=auth_headers)
    assert listed.json()["by_category"] == {"Sonstiges": 5.0}


async def test_totals_sum_across_categories(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/expenses", json={"amount": 10.0, "description": "Bus", "category": "Transport"}, headers=auth_headers
    )
    await client.post(
        "/expenses", json={"amount": 20.0, "description": "Taxi", "category": "Transport"}, headers=auth_headers
    )
    await client.post(
        "/expenses", json={"amount": 30.0, "description": "Kino", "category": "Freizeit"}, headers=auth_headers
    )

    listed = await client.get("/expenses", headers=auth_headers)
    data = listed.json()
    assert data["total"] == 60.0
    assert data["by_category"] == {"Transport": 30.0, "Freizeit": 30.0}


async def test_filter_by_category(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/expenses", json={"amount": 10.0, "description": "Bus", "category": "Transport"}, headers=auth_headers
    )
    await client.post(
        "/expenses", json={"amount": 30.0, "description": "Kino", "category": "Freizeit"}, headers=auth_headers
    )

    listed = await client.get("/expenses?category=Transport", headers=auth_headers)
    data = listed.json()
    assert len(data["expenses"]) == 1
    assert data["total"] == 10.0


async def test_delete_expense(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/expenses", json={"amount": 12.5, "description": "Mittagessen"}, headers=auth_headers
    )
    expense_id = created.json()["id"]

    deleted = await client.delete(f"/expenses/{expense_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed = await client.get("/expenses", headers=auth_headers)
    assert listed.json()["expenses"] == []


async def test_delete_foreign_expense_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/expenses/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_chat_tool_adds_expense(client: AsyncClient, auth_headers: dict, monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "add_expense",
                            "arguments": {"amount": 12.5, "description": "Mittagessen", "category": "Essen"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Eingetragen.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Ich hab 12,50 für Mittagessen ausgegeben"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["amount"] == 12.5

    listed = await client.get("/expenses", headers=auth_headers)
    assert listed.json()["total"] == 12.5

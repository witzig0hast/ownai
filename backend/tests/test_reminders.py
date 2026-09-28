from httpx import AsyncClient

from app.services import ollama_client


async def test_create_list_update_delete_daily_reminder(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/reminders",
        json={"label": "Tabletten nehmen", "recurrence": "daily", "hour": 8, "minute": 0},
        headers=auth_headers,
    )
    assert created.status_code == 201
    reminder = created.json()
    assert reminder["label"] == "Tabletten nehmen"
    assert reminder["active"] is True
    reminder_id = reminder["id"]

    listed = await client.get("/reminders", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["reminders"]) == 1

    updated = await client.patch(f"/reminders/{reminder_id}", json={"active": False}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    deleted = await client.delete(f"/reminders/{reminder_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed_again = await client.get("/reminders", headers=auth_headers)
    assert listed_again.json()["reminders"] == []


async def test_weekly_reminder_requires_weekday(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/reminders",
        json={"label": "Müll rausbringen", "recurrence": "weekly", "hour": 20, "minute": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_monthly_reminder_requires_day_of_month(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/reminders",
        json={"label": "Miete überweisen", "recurrence": "monthly", "hour": 9, "minute": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_delete_foreign_reminder_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/reminders/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_chat_tool_adds_reminder(client: AsyncClient, auth_headers: dict, monkeypatch):
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
                            "name": "add_reminder",
                            "arguments": {
                                "label": "Wasser trinken",
                                "recurrence": "daily",
                                "hour": 10,
                                "minute": 30,
                            },
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Erledigt.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]
    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Erinnere mich jeden Tag um 10:30 Uhr, Wasser zu trinken"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["label"] == "Wasser trinken"

    listed = await client.get("/reminders", headers=auth_headers)
    assert listed.json()["reminders"][0]["label"] == "Wasser trinken"

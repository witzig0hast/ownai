from httpx import AsyncClient

from app.services import ollama_client


async def test_create_list_update_delete_automation(client: AsyncClient, auth_headers: dict):
    created = await client.post(
        "/automations",
        json={"entity_id": "lock.haustuer", "trigger_state": "unlocked", "message": "Tür ist auf"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    automation = created.json()
    assert automation["entity_id"] == "lock.haustuer"
    assert automation["active"] is True
    automation_id = automation["id"]

    listed = await client.get("/automations", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["automations"]) == 1

    updated = await client.patch(f"/automations/{automation_id}", json={"active": False}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    deleted = await client.delete(f"/automations/{automation_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed_again = await client.get("/automations", headers=auth_headers)
    assert listed_again.json()["automations"] == []


async def test_delete_foreign_automation_is_404(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/automations/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


async def test_chat_tool_adds_automation(client: AsyncClient, auth_headers: dict, monkeypatch):
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
                            "name": "add_automation",
                            "arguments": {
                                "entity_id": "lock.haustuer",
                                "trigger_state": "unlocked",
                                "message": "Tür ist auf",
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
        json={"content": "Warne mich, wenn die Haustür aufgeschlossen wird"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["entity_id"] == "lock.haustuer"

    listed = await client.get("/automations", headers=auth_headers)
    assert listed.json()["automations"][0]["entity_id"] == "lock.haustuer"

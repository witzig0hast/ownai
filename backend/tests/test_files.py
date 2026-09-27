from httpx import AsyncClient

from app.services import ollama_client


async def test_create_file_tool_writes_and_lists_txt_file(client: AsyncClient, auth_headers: dict, monkeypatch):
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
                            "name": "create_file",
                            "arguments": {
                                "filename": "Einkaufsliste.txt",
                                "content": "Milch\nBrot\nEier",
                                "format": "txt",
                            },
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Datei erstellt.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schreib mir eine Einkaufsliste"},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["filename"] == "Einkaufsliste.txt"
    file_id = result["id"]

    listed = await client.get(f"/chat/conversations/{conversation_id}/files", headers=auth_headers)
    assert listed.status_code == 200
    files = listed.json()["files"]
    assert len(files) == 1
    assert files[0]["id"] == file_id
    assert files[0]["filename"] == "Einkaufsliste.txt"
    assert files[0]["mime_type"] == "text/plain"

    downloaded = await client.get(
        f"/chat/conversations/{conversation_id}/files/{file_id}", headers=auth_headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"Milch\nBrot\nEier"


async def test_create_file_tool_renders_pdf(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "create_file",
                            "arguments": {
                                "filename": "Bericht",
                                "content": "Hallo Wörld, äöü ß!",
                                "format": "pdf",
                            },
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "PDF erstellt.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Erstell mir ein PDF"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["filename"] == "Bericht.pdf"

    downloaded = await client.get(
        f"/chat/conversations/{conversation_id}/files/{result['id']}", headers=auth_headers
    )
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert downloaded.content.startswith(b"%PDF")


async def test_files_are_scoped_per_conversation_and_owner(client: AsyncClient, auth_headers: dict):
    from app.services import file_service

    conv_a = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conv_b = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_a_id = conv_a.json()["id"]
    conversation_b_id = conv_b.json()["id"]

    from app.db.session import async_session_maker

    async with async_session_maker() as db:
        from app.db.models import Conversation, User
        from sqlalchemy import select

        user = (await db.execute(select(User))).scalar_one()
        conversation_a = await db.get(Conversation, conversation_a_id)
        record = await file_service.create_file(
            db, user, conversation_a, filename="geheim.txt", content="top secret", file_format="txt"
        )

    other_conv_download = await client.get(
        f"/chat/conversations/{conversation_b_id}/files/{record.id}", headers=auth_headers
    )
    assert other_conv_download.status_code == 404

    same_conv_download = await client.get(
        f"/chat/conversations/{conversation_a_id}/files/{record.id}", headers=auth_headers
    )
    assert same_conv_download.status_code == 200


async def test_create_file_rejects_empty_content(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "create_file", "arguments": {"filename": "leer.txt", "content": "  "}}}
                ],
            }
        return {"role": "assistant", "content": "Ging nicht.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Leere Datei bitte"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert "error" in result

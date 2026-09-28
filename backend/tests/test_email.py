import socket

from httpx import AsyncClient

from app.services import email_service, ollama_client


async def test_email_status_unconfigured_by_default(client: AsyncClient, auth_headers: dict):
    response = await client.get("/integrations/email", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"has_custom_account": False, "effective_from_address": None}


async def test_connect_email_then_status_reflects_it(client: AsyncClient, auth_headers: dict):
    connect = await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )
    assert connect.status_code == 200
    assert connect.json() == {"connected": True}

    status = await client.get("/integrations/email", headers=auth_headers)
    assert status.json() == {"has_custom_account": True, "effective_from_address": "karim@example.com"}


async def test_send_email_tool_uses_connected_account(client: AsyncClient, auth_headers: dict, monkeypatch):
    await client.post(
        "/integrations/email",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "karim",
            "smtp_password": "s3cret",
            "from_address": "karim@example.com",
        },
        headers=auth_headers,
    )

    sent_messages = []

    def fake_send_sync(config, to, subject, body):
        sent_messages.append((config.from_address, to, subject, body))

    monkeypatch.setattr(email_service, "_send_sync", fake_send_sync)

    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "send_email",
                            "arguments": {
                                "to": "empfaenger@example.com",
                                "subject": "Hallo",
                                "body": "Testnachricht",
                            },
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "E-Mail gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine E-Mail"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result == {"sent": True, "to": "empfaenger@example.com"}
    assert sent_messages == [("karim@example.com", "empfaenger@example.com", "Hallo", "Testnachricht")]


async def test_send_email_tool_reports_error_when_unconfigured(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_chat(messages, tools=None):  # noqa: ARG001
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "send_email",
                            "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hi"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Ging nicht.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine E-Mail"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert "error" in result


def test_connect_ipv4_only_requests_af_inet(monkeypatch):
    """_connect_ipv4 must ask getaddrinfo for AF_INET explicitly - the whole point is to never
    even consider an AAAA/IPv6 result, not just to prefer IPv4 among mixed results."""
    seen_family = {}

    class FakeSocket:
        def __init__(self, family, socktype, proto):
            self.family = family

        def settimeout(self, timeout):
            pass

        def connect(self, sockaddr):
            pass

        def close(self):
            pass

    def fake_getaddrinfo(host, port, family, socktype):
        seen_family["family"] = family
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]

    monkeypatch.setattr(email_service.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(email_service.socket, "socket", FakeSocket)

    result = email_service._connect_ipv4("smtp.example.com", 587, 15)

    assert seen_family["family"] == socket.AF_INET
    assert isinstance(result, FakeSocket)


def test_connect_ipv4_raises_last_error_when_all_attempts_fail(monkeypatch):
    class FailingSocket:
        def __init__(self, *args):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, sockaddr):
            raise OSError(101, "Network is unreachable")

        def close(self):
            pass

    def fake_getaddrinfo(host, port, family, socktype):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]

    monkeypatch.setattr(email_service.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(email_service.socket, "socket", FailingSocket)

    try:
        email_service._connect_ipv4("smtp.example.com", 587, 15)
        assert False, "expected OSError"
    except OSError as exc:
        assert "Network is unreachable" in str(exc)

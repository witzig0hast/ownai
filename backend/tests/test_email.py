import socket
from email.message import EmailMessage as StdlibEmailMessage

from httpx import AsyncClient

from app.services import email_service, ollama_client
from tests.conftest import drain_background_tasks


def _build_raw_email(frm: str, subject: str, body: str, *, html: bool = False) -> bytes:
    msg = StdlibEmailMessage()
    msg["From"] = frm
    msg["Subject"] = subject
    if html:
        msg.set_content(body, subtype="html")
    else:
        msg.set_content(body)
    return msg.as_bytes()


async def _connect_smtp(client: AsyncClient, auth_headers: dict) -> None:
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


async def test_email_status_unconfigured_by_default(client: AsyncClient, auth_headers: dict):
    response = await client.get("/integrations/email", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "has_custom_account": False,
        "effective_from_address": None,
        "has_imap_account": False,
        "inbound_agent_enabled": False,
    }


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
    assert status.json() == {
        "has_custom_account": True,
        "effective_from_address": "karim@example.com",
        "has_imap_account": False,
        "inbound_agent_enabled": False,
    }


async def test_send_email_tool_queues_immediately_then_sends_in_background(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """The tool call itself must return right away (queued, not sent) - the actual SMTP work
    happens afterwards, detached from the chat response (see app/agent/tools.py::_send_email).
    Blocking the chat turn on SMTP round-trip time is exactly what caused real 504s."""
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
        return {"role": "assistant", "content": "E-Mail wird gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine E-Mail"},
        headers=auth_headers,
    )
    # The tool's own result is "queued", never "sent" - whether the background task has
    # actually run by the time this response comes back isn't guaranteed either way (it depends
    # on event-loop scheduling), so that's not asserted here; what matters is that the chat turn
    # itself never awaited the SMTP call to find out.
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["queued"] is True
    assert result["to"] == "empfaenger@example.com"
    assert "sent" not in result

    await drain_background_tasks()
    assert sent_messages == [("karim@example.com", "empfaenger@example.com", "Hallo", "Testnachricht")]


async def test_send_email_tool_logs_error_when_unconfigured(client: AsyncClient, auth_headers: dict, monkeypatch):
    """Still queues immediately even with no SMTP account connected - the "not configured" error
    only surfaces afterwards, as a log entry (Settings -> Logs), not in the tool's own result."""

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
        return {"role": "assistant", "content": "Wird gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine E-Mail"},
        headers=auth_headers,
    )
    result = sent.json()["message"]["tool_calls"][0]["result"]
    assert result["queued"] is True

    await drain_background_tasks()
    logs = await client.get("/logs?category=email", headers=auth_headers)
    entries = logs.json()["logs"]
    assert len(entries) == 1
    assert entries[0]["level"] == "error"


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


def test_ipv4_smtp_ssl_wraps_with_tls_immediately(monkeypatch):
    """_IPv4SMTP_SSL._get_socket must hand back a TLS-wrapped socket directly - no plaintext SMTP
    exchange ever happens on an implicit-TLS (port 465) connection, unlike STARTTLS."""
    wrapped = {}

    class FakeContext:
        def wrap_socket(self, sock, server_hostname=None):
            wrapped["sock"] = sock
            wrapped["server_hostname"] = server_hostname
            return "tls-wrapped-socket"

    fake_plain_socket = object()
    monkeypatch.setattr(email_service, "_connect_ipv4", lambda host, port, timeout: fake_plain_socket)  # noqa: ARG005

    instance = object.__new__(email_service._IPv4SMTP_SSL)
    instance.context = FakeContext()
    instance._host = "smtp.example.com"

    result = instance._get_socket("smtp.example.com", 465, 15)

    assert result == "tls-wrapped-socket"
    assert wrapped["sock"] is fake_plain_socket
    assert wrapped["server_hostname"] == "smtp.example.com"


def test_send_sync_uses_implicit_tls_for_port_465(monkeypatch):
    """Port 465 is implicit TLS (SMTPS) by convention (RFC 8314) - speaking plaintext-then-
    STARTTLS there instead doesn't get a clean rejection, the server just hangs waiting for a TLS
    handshake that never comes and eventually drops the connection ("Connection unexpectedly
    closed: timed out" - exactly the symptom that looked like a network/firewall issue for so
    long, since the TCP connection itself really was fine)."""
    calls = {"ssl_init": 0, "starttls": 0}

    class FakeSMTPSSL:
        def __init__(self, host, port, timeout=None, local_hostname=None):  # noqa: ARG002
            calls["ssl_init"] += 1

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def starttls(self):
            calls["starttls"] += 1

        def login(self, username, password):  # noqa: ARG002
            pass

        def send_message(self, message):  # noqa: ARG002
            pass

    monkeypatch.setattr(email_service, "_IPv4SMTP_SSL", FakeSMTPSSL)

    config = email_service._EffectiveConfig("smtp.example.com", 465, "user", "pass", "from@example.com", True)
    email_service._send_sync(config, "to@example.com", "Subject", "Body")

    assert calls["ssl_init"] == 1
    assert calls["starttls"] == 0  # never STARTTLS on an implicit-TLS connection


def test_send_sync_still_uses_starttls_for_port_587(monkeypatch):
    """Regression guard: the implicit-TLS path for port 465 must not change behavior for the
    far more common STARTTLS ports (587/25)."""
    calls = {"plain_init": 0, "starttls": 0}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None, local_hostname=None):  # noqa: ARG002
            calls["plain_init"] += 1

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def starttls(self):
            calls["starttls"] += 1

        def login(self, username, password):  # noqa: ARG002
            pass

        def send_message(self, message):  # noqa: ARG002
            pass

    monkeypatch.setattr(email_service, "_IPv4SMTP", FakeSMTP)

    config = email_service._EffectiveConfig("smtp.example.com", 587, "user", "pass", "from@example.com", True)
    email_service._send_sync(config, "to@example.com", "Subject", "Body")

    assert calls["plain_init"] == 1
    assert calls["starttls"] == 1


async def test_send_email_timeout_gets_logged_with_clear_message(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """A raw connect/response timeout must surface (in the log entry, since the tool result
    itself no longer carries it - see above) as an explanation naming the mail server and the
    likely (server-side) cause, not just the bare "timed out" text of str(TimeoutError())."""
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

    def fake_send_sync(config, to, subject, body):  # noqa: ARG001
        raise TimeoutError("timed out")

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
                            "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hi"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Wird gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine Test-Mail"},
        headers=auth_headers,
    )
    await drain_background_tasks()

    logs = await client.get("/logs?category=email", headers=auth_headers)
    entry = logs.json()["logs"][0]
    assert "smtp.example.com:587" in entry["message"]
    assert "Timeout" in entry["message"]
    assert entry["message"] != "timed out"  # the old, unhelpful raw exception text alone


def test_send_sync_reports_send_phase_on_failure(monkeypatch):
    """A failure while actually handing the message to the server must be reported as the "send"
    phase specifically (not retried - there's no retry at all anymore, see send_email_in_background:
    SMTP now always runs detached from any request, so a failed attempt is simply logged and the
    user/model can ask to retry, rather than this layer silently retrying and risking a duplicate
    delivery if the server had already accepted the message)."""
    calls = {"send": 0}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None, local_hostname=None):  # noqa: ARG002
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def starttls(self):
            pass

        def login(self, username, password):  # noqa: ARG002
            pass

        def send_message(self, message):  # noqa: ARG002
            calls["send"] += 1
            raise OSError("simulated failure during send")

    monkeypatch.setattr(email_service, "_IPv4SMTP", FakeSMTP)

    config = email_service._EffectiveConfig("smtp.example.com", 587, "user", "pass", "from@example.com", True)
    try:
        email_service._send_sync(config, "to@example.com", "Subject", "Body")
        assert False, "expected _SendPhaseError"
    except email_service._SendPhaseError as exc:
        assert exc.phase == "send"

    assert calls["send"] == 1


async def test_send_email_reports_which_phase_failed(client: AsyncClient, auth_headers: dict, monkeypatch):
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

    def fake_send_sync(config, to, subject, body):  # noqa: ARG001
        raise email_service._SendPhaseError("login", OSError("bad credentials"))

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
                            "arguments": {"to": "x@example.com", "subject": "Hi", "body": "Hi"},
                        }
                    }
                ],
            }
        return {"role": "assistant", "content": "Wird gesendet.", "tool_calls": []}

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    created = await client.post("/chat/conversations", json={}, headers=auth_headers)
    conversation_id = created.json()["id"]

    await client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"content": "Schick eine Test-Mail"},
        headers=auth_headers,
    )
    await drain_background_tasks()

    logs = await client.get("/logs?category=email", headers=auth_headers)
    entry = logs.json()["logs"][0]
    assert "Anmeldung" in entry["message"]
    assert "bad credentials" in entry["detail"]


async def test_connect_imap_requires_smtp_connected_first(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/integrations/email/imap",
        json={"imap_host": "imap.example.com", "imap_port": 993, "imap_username": "karim", "imap_password": "s3cret"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "imap_not_configured"


async def test_connect_imap_then_status_reflects_it(client: AsyncClient, auth_headers: dict):
    await _connect_smtp(client, auth_headers)

    connect = await client.post(
        "/integrations/email/imap",
        json={"imap_host": "imap.example.com", "imap_port": 993, "imap_username": "karim", "imap_password": "s3cret"},
        headers=auth_headers,
    )
    assert connect.status_code == 200
    assert connect.json() == {"connected": True}

    status = await client.get("/integrations/email", headers=auth_headers)
    body = status.json()
    assert body["has_imap_account"] is True
    assert body["inbound_agent_enabled"] is False


async def test_enable_inbound_agent_requires_imap_connected_first(client: AsyncClient, auth_headers: dict):
    await _connect_smtp(client, auth_headers)

    response = await client.patch(
        "/integrations/email/inbound-agent", json={"enabled": True}, headers=auth_headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "imap_not_configured"


async def test_enable_then_disable_inbound_agent(client: AsyncClient, auth_headers: dict):
    await _connect_smtp(client, auth_headers)
    await client.post(
        "/integrations/email/imap",
        json={"imap_host": "imap.example.com", "imap_port": 993, "imap_username": "karim", "imap_password": "s3cret"},
        headers=auth_headers,
    )

    enabled = await client.patch(
        "/integrations/email/inbound-agent", json={"enabled": True}, headers=auth_headers
    )
    assert enabled.status_code == 200
    assert enabled.json()["inbound_agent_enabled"] is True

    disabled = await client.patch(
        "/integrations/email/inbound-agent", json={"enabled": False}, headers=auth_headers
    )
    assert disabled.json()["inbound_agent_enabled"] is False


def test_parse_email_extracts_plain_text_body():
    raw = _build_raw_email("Absender <a@example.com>", "Testbetreff", "Hallo Welt")
    result = email_service._parse_email(raw)
    assert result["from"] == "Absender <a@example.com>"
    assert result["subject"] == "Testbetreff"
    assert "Hallo Welt" in result["body"]


def test_parse_email_strips_html_markup_from_html_only_body():
    raw = _build_raw_email("a@example.com", "HTML-Mail", "<p>Hallo <b>Welt</b></p>", html=True)
    result = email_service._parse_email(raw)
    assert "<p>" not in result["body"]
    assert "<b>" not in result["body"]
    assert "Hallo" in result["body"]
    assert "Welt" in result["body"]


class _FakeImap:
    """Minimal stand-in for the subset of imaplib's interface _fetch_unseen_sync uses."""

    instances: list["_FakeImap"] = []

    def __init__(self, host, port, timeout=None):  # noqa: ARG002
        self.host = host
        self.port = port
        _FakeImap.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def login(self, username, password):  # noqa: ARG002
        pass

    def select(self, mailbox):  # noqa: ARG002
        return ("OK", [b"1"])

    def search(self, charset, criterion):  # noqa: ARG002
        return ("OK", [b"1"])

    def fetch(self, num, parts):  # noqa: ARG002
        raw = _build_raw_email("Absender <a@example.com>", "Testbetreff", "Hallo Welt")
        return ("OK", [(b"1 (RFC822 {%d}" % len(raw), raw)])


def test_fetch_unseen_sync_uses_implicit_tls_class_for_port_993(monkeypatch):
    _FakeImap.instances = []
    monkeypatch.setattr(email_service, "_IPv4IMAP4_SSL", _FakeImap)

    messages = email_service._fetch_unseen_sync("imap.example.com", 993, "karim", "s3cret")

    assert len(_FakeImap.instances) == 1
    assert len(messages) == 1
    assert messages[0]["subject"] == "Testbetreff"


def test_fetch_unseen_sync_uses_plain_class_for_other_ports(monkeypatch):
    _FakeImap.instances = []
    monkeypatch.setattr(email_service, "_IPv4IMAP4", _FakeImap)

    messages = email_service._fetch_unseen_sync("imap.example.com", 143, "karim", "s3cret")

    assert len(_FakeImap.instances) == 1
    assert len(messages) == 1

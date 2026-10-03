import asyncio
import email as email_lib
import imaplib
import smtplib
import socket
from email import policy
from email.message import EmailMessage

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import EmailAccount, User
from app.db.session import async_session_maker
from app.errors import APIError
from app.services import log_service
from app.services.crypto import decrypt, encrypt


class EmailNotConfigured(APIError):
    def __init__(self, message: str = "Keine E-Mail-Konfiguration verfügbar (weder eigene noch System-Standard)."):
        super().__init__(409, "email_not_configured", message)


class EmailSendFailed(APIError):
    def __init__(self, message: str):
        super().__init__(502, "email_send_failed", message)


class ImapNotConfigured(APIError):
    def __init__(self, message: str = "Kein SMTP-Konto verbunden - verbinde zuerst POST /integrations/email."):
        super().__init__(409, "imap_not_configured", message)


async def get_account(db: AsyncSession, user: User) -> EmailAccount | None:
    result = await db.execute(select(EmailAccount).where(EmailAccount.user_id == user.id))
    return result.scalar_one_or_none()


async def connect(
    db: AsyncSession,
    user: User,
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    from_address: str,
    use_tls: bool,
) -> EmailAccount:
    existing = await get_account(db, user)
    if existing is not None:
        existing.smtp_host = smtp_host
        existing.smtp_port = smtp_port
        existing.smtp_username = smtp_username
        existing.encrypted_smtp_password = encrypt(smtp_password)
        existing.from_address = from_address
        existing.use_tls = use_tls
        account = existing
    else:
        account = EmailAccount(
            user_id=user.id,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            encrypted_smtp_password=encrypt(smtp_password),
            from_address=from_address,
            use_tls=use_tls,
        )
        db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def connect_imap(
    db: AsyncSession,
    user: User,
    *,
    imap_host: str,
    imap_port: int,
    imap_username: str,
    imap_password: str,
) -> EmailAccount:
    """Sets the IMAP side of the user's EmailAccount (see app/services/email_inbox_service.py) -
    requires an EmailAccount row to already exist (i.e. SMTP connected first, see connect()
    above), since smtp_host/smtp_username/etc. are NOT NULL on that row."""
    account = await get_account(db, user)
    if account is None:
        raise ImapNotConfigured()
    account.imap_host = imap_host
    account.imap_port = imap_port
    account.imap_username = imap_username
    account.encrypted_imap_password = encrypt(imap_password)
    await db.commit()
    await db.refresh(account)
    return account


async def set_inbound_agent_enabled(db: AsyncSession, user: User, enabled: bool) -> EmailAccount:
    account = await get_account(db, user)
    if account is None or account.imap_host is None:
        raise ImapNotConfigured("Kein IMAP-Konto verbunden - verbinde zuerst POST /integrations/email/imap.")
    account.inbound_agent_enabled = enabled
    await db.commit()
    await db.refresh(account)
    return account


class _EffectiveConfig:
    def __init__(self, host: str, port: int, username: str, password: str, from_address: str, use_tls: bool):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.use_tls = use_tls


async def effective_config(db: AsyncSession, user: User) -> _EffectiveConfig | None:
    """The user's own connected SMTP account if they have one, otherwise the system-wide default
    from settings (SYSTEM_SMTP_*), otherwise None (send_email then raises EmailNotConfigured)."""
    account = await get_account(db, user)
    if account is not None:
        return _EffectiveConfig(
            account.smtp_host,
            account.smtp_port,
            account.smtp_username,
            decrypt(account.encrypted_smtp_password),
            account.from_address,
            account.use_tls,
        )
    settings = get_settings()
    if settings.system_smtp_host and settings.system_smtp_from_address:
        return _EffectiveConfig(
            settings.system_smtp_host,
            settings.system_smtp_port,
            settings.system_smtp_username or "",
            settings.system_smtp_password or "",
            settings.system_smtp_from_address,
            settings.system_smtp_use_tls,
        )
    return None


def _connect_ipv4(host: str, port: int, timeout: float) -> socket.socket:
    """Like socket.create_connection(), but only tries IPv4 (A) addresses, never IPv6 (AAAA).

    Docker containers commonly have an IPv6 address on their interface with no actual IPv6
    route to the internet (host/VPN routing only handles IPv4). getaddrinfo()'s default address
    order often puts an AAAA record first, so plain socket.create_connection()/smtplib then
    tries to connect over IPv6 first and fails immediately with OSError [Errno 101] "Network is
    unreachable" - even though IPv4 would work fine. Forcing IPv4 sidesteps that entirely."""
    last_error: OSError | None = None
    for family, socktype, proto, _canonname, sockaddr in socket.getaddrinfo(
        host, port, socket.AF_INET, socket.SOCK_STREAM
    ):
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(timeout)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_error = exc
            sock.close()
    raise last_error or OSError(f"Konnte {host}:{port} nicht per IPv4 auflösen/erreichen.")


class _IPv4SMTP(smtplib.SMTP):
    """smtplib.SMTP, but its socket connects over IPv4 only (see _connect_ipv4). TLS hostname
    verification in starttls() still checks against the original hostname (self._host), which
    smtplib sets from the constructor argument below unchanged - swapping to an IPv4-only
    *connection* doesn't affect that."""

    def _get_socket(self, host: str, port: int, timeout: float) -> socket.socket:
        if timeout is not None and not timeout:
            raise OSError("nonblocking socket (timeout=0) is not supported")
        return _connect_ipv4(host, port, timeout)


# Port 465 is, by long-standing convention (and explicitly in RFC 8314), *implicit* TLS/SMTPS:
# the server expects a TLS handshake as the very first bytes on the connection, never plaintext
# SMTP first. That's a different protocol from STARTTLS (587/25: connect in plaintext, send
# EHLO, then upgrade via the STARTTLS command) - speaking STARTTLS at a server configured for
# implicit TLS doesn't get rejected with a clear error, it just hangs: the server is waiting for
# a TLS ClientHello that never comes, and eventually drops the connection. That surfaces as
# exactly "Connection unexpectedly closed: timed out" - indistinguishable, from the client's
# side, from a genuinely slow/unreachable server, which is why this went undiagnosed through
# extensive *network*-level checks (routing, firewall, reachability) that all correctly found
# nothing wrong: the TCP connection itself was never the problem.
_IMPLICIT_TLS_PORT = 465


class _IPv4SMTP_SSL(smtplib.SMTP_SSL):
    """smtplib.SMTP_SSL (implicit TLS from the first byte, for _IMPLICIT_TLS_PORT), with the
    same IPv4-only connection as _IPv4SMTP above."""

    def _get_socket(self, host: str, port: int, timeout: float) -> socket.socket:
        if timeout is not None and not timeout:
            raise OSError("nonblocking socket (timeout=0) is not supported")
        return self.context.wrap_socket(_connect_ipv4(host, port, timeout), server_hostname=self._host)


class _SendPhaseError(Exception):
    """Carries which step of the SMTP conversation failed, so callers can report something more
    useful than a bare exception string - see send_email's error handling."""

    def __init__(self, phase: str, original: Exception):
        self.phase = phase
        self.original = original
        super().__init__(str(original))


def _send_sync(config: _EffectiveConfig, to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = config.from_address
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    # Explicit local_hostname skips smtplib's default behavior of calling socket.getfqdn() to
    # guess one - a reverse-DNS lookup of the *container's own* address with no timeout control
    # of its own, unrelated to this connection's target. In a Docker container this can be slow
    # or hang, eating into the time budget before the actual SMTP conversation even starts,
    # which then surfaces later as a misleading "Connection unexpectedly closed: timed out" once
    # the real timeout finally fires (see smtplib.SMTP.getreply(), which wraps any OSError from
    # reading the socket - including a plain timeout - in that message). The EHLO hostname is
    # informational only for any well-behaved server, so a static value is safe here.
    # 60s: some servers deliberately slow down the SMTP dialogue (spam scoring,
    # greylisting-style delays) for senders they haven't seen before/don't fully trust yet,
    # rather than rejecting outright - a real "250 OK" can take a while longer than a normal
    # fast exchange without anything actually being broken.
    #
    # Deliberately a single attempt, no built-in retry: send_email() now always runs detached in
    # the background (see send_email_in_background) rather than blocking a chat response, so
    # there's no user-facing deadline this needs to race against - a failed attempt is simply
    # logged (Settings -> Logs) and the user/model can ask to retry if they want to.
    implicit_tls = config.use_tls and config.port == _IMPLICIT_TLS_PORT
    smtp_cls = _IPv4SMTP_SSL if implicit_tls else _IPv4SMTP

    phase = "connect"
    try:
        with smtp_cls(config.host, config.port, timeout=60, local_hostname="ownai-backend") as smtp:
            if config.use_tls and not implicit_tls:
                phase = "starttls"
                smtp.starttls()
            if config.username and config.password:
                phase = "login"
                smtp.login(config.username, config.password)
            phase = "send"
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise _SendPhaseError(phase, exc) from exc


_PHASE_LABELS = {
    "connect": "beim Verbindungsaufbau",
    "starttls": "bei der TLS-Verschlüsselung (STARTTLS)",
    "login": "bei der Anmeldung (Login)",
    "send": "beim eigentlichen Versenden der Nachricht",
}


async def _log_failure(db: AsyncSession, user: User, config: _EffectiveConfig, message: str, detail: str) -> None:
    await log_service.log(
        db,
        category="email",
        level="error",
        user=user,
        message=f"{message} ({config.host}:{config.port})",
        detail=detail,
    )


async def send_email(db: AsyncSession, user: User, to: str, subject: str, body: str) -> None:
    config = await effective_config(db, user)
    if config is None:
        await log_service.log(
            db,
            category="email",
            level="error",
            user=user,
            message="E-Mail nicht gesendet: keine SMTP-Konfiguration vorhanden (weder eigene noch System-Standard).",
        )
        raise EmailNotConfigured()
    try:
        # smtplib is blocking I/O - runs in a worker thread so it doesn't stall the event loop.
        await asyncio.to_thread(_send_sync, config, to, subject, body)
    except _SendPhaseError as exc:
        where = _PHASE_LABELS.get(exc.phase, exc.phase)
        if isinstance(exc.original, TimeoutError):
            await _log_failure(db, user, config, f"Timeout {where}", str(exc.original))
            raise EmailSendFailed(
                f"Der Mailserver ({config.host}:{config.port}) hat {where} nicht rechtzeitig "
                "geantwortet (Timeout). Das liegt meist am Mailserver selbst, nicht an OwnAI - "
                "z.B. absichtliche Verzögerung bei neuen/unbekannten Absendern (Spam-Schutz). "
                "Erneut versuchen oder beim Mailserver-Betreiber nachfragen."
            ) from exc
        await _log_failure(db, user, config, f"Fehler {where}", str(exc.original))
        raise EmailSendFailed(f"E-Mail konnte nicht gesendet werden ({where}): {exc.original}") from exc
    except TimeoutError as exc:
        # Defense in depth - _send_sync always wraps its own failures in _SendPhaseError, but
        # don't assume it's the only possible source of a bare exception here.
        await _log_failure(db, user, config, "Timeout", str(exc))
        raise EmailSendFailed(
            f"Der Mailserver ({config.host}:{config.port}) hat nicht rechtzeitig geantwortet (Timeout)."
        ) from exc
    except (smtplib.SMTPException, OSError) as exc:
        await _log_failure(db, user, config, "Fehler beim Versand", str(exc))
        raise EmailSendFailed(f"E-Mail konnte nicht gesendet werden: {exc}") from exc
    else:
        await log_service.log(
            db,
            category="email",
            level="info",
            user=user,
            message=f"E-Mail an {to} erfolgreich gesendet (Betreff: \"{subject}\").",
        )


async def send_email_in_background(user_id: str, to: str, subject: str, body: str) -> None:
    """Runs send_email() fully detached from whatever call queued it (see app/agent/tools.py's
    send_email tool, fired via app/utils.py's fire_and_forget) - SMTP can legitimately take tens
    of seconds against a slow/greylisting mail server, and that must never block a chat response.
    Opens its own DB session since the caller's request-scoped one will already be closed by the
    time this runs. send_email() already logs every outcome via log_service (success and every
    failure path) - by the time it raises here, there is no caller left to hand the error to, so
    this only needs to stop it from propagating as an unretrieved task exception."""
    async with async_session_maker() as db:
        user = await db.get(User, user_id)
        if user is None:
            return
        try:
            await send_email(db, user, to, subject, body)
        except APIError:
            pass


# IMAP, for the "eingehende E-Mails" inbound agent (app/services/email_inbox_service.py). Same
# IPv4-only-connection rationale as SMTP above, and the same implicit-TLS-vs-STARTTLS lesson:
# port 993 is implicit TLS by convention, so it gets IMAP4_SSL directly rather than IMAP4 +
# STARTTLS. Unlike SMTP (587/465 both common), virtually every real-world IMAP server uses 993 -
# a plaintext/STARTTLS IMAP path is deliberately not implemented here, kept to the already-tested
# IPv4 plain socket for the rare local/LAN case where 993 isn't used.
_IMAP_IMPLICIT_TLS_PORT = 993
_IMAP_FETCH_TIMEOUT_SECONDS = 30
MAX_EMAIL_BODY_CHARS = 4000


class _IPv4IMAP4_SSL(imaplib.IMAP4_SSL):
    """imaplib.IMAP4_SSL, but its socket connects over IPv4 only (see _connect_ipv4)."""

    def _create_socket(self, timeout):
        sock = _connect_ipv4(self.host, self.port, timeout if timeout is not None else _IMAP_FETCH_TIMEOUT_SECONDS)
        return self.ssl_context.wrap_socket(sock, server_hostname=self.host)


class _IPv4IMAP4(imaplib.IMAP4):
    """imaplib.IMAP4 (plaintext, no TLS) with the same IPv4-only connection - only reached for a
    non-993 port, see _IMAP_IMPLICIT_TLS_PORT above."""

    def _create_socket(self, timeout):
        return _connect_ipv4(self.host, self.port, timeout if timeout is not None else _IMAP_FETCH_TIMEOUT_SECONDS)


def _extract_plain_text(part) -> str:
    """get_body() can hand back a text/plain or text/html part depending on what the message
    offers - strip markup for the latter with the same BeautifulSoup-based approach already used
    for web pages (see clipper_service.py), rather than showing raw HTML to the model."""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        content = BeautifulSoup(content, "html.parser").get_text(separator="\n", strip=True)
    return content


def _parse_email(raw: bytes) -> dict:
    msg = email_lib.message_from_bytes(raw, policy=policy.default)
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = _extract_plain_text(body_part) if body_part is not None else ""
    return {
        "from": str(msg.get("From", "")),
        "subject": str(msg.get("Subject", "")) or "(kein Betreff)",
        "body": body[:MAX_EMAIL_BODY_CHARS],
    }


def _fetch_unseen_sync(host: str, port: int, username: str, password: str) -> list[dict]:
    """Connects, logs in, and returns every UNSEEN message in INBOX as {"from", "subject",
    "body"} dicts - marks each \\Seen as it's fetched (standard IMAP idiom: imaplib's FETCH
    implicitly sets \\Seen unless done with BODY.PEEK, which is exactly what we want here so the
    next poll doesn't see it again). Blocking I/O - runs in a worker thread, see
    fetch_unseen_emails."""
    imap_cls = _IPv4IMAP4_SSL if port == _IMAP_IMPLICIT_TLS_PORT else _IPv4IMAP4
    messages: list[dict] = []
    with imap_cls(host, port, timeout=_IMAP_FETCH_TIMEOUT_SECONDS) as imap:
        imap.login(username, password)
        imap.select("INBOX")
        status, data = imap.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return messages
        for num in data[0].split():
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            messages.append(_parse_email(msg_data[0][1]))
    return messages


async def fetch_unseen_emails(db: AsyncSession, user: User) -> list[dict]:
    """Returns every unseen inbox message for the user's configured IMAP account as a list of
    {"from", "subject", "body"} dicts (empty list if IMAP isn't configured - best-effort, not an
    error, since this runs from a scheduler poll with no one to show an error to)."""
    account = await get_account(db, user)
    if account is None or account.imap_host is None or account.imap_port is None:
        return []
    password = decrypt(account.encrypted_imap_password) if account.encrypted_imap_password else ""
    try:
        return await asyncio.to_thread(
            _fetch_unseen_sync, account.imap_host, account.imap_port, account.imap_username or "", password
        )
    except (imaplib.IMAP4.error, OSError) as exc:
        await log_service.log(
            db,
            category="email",
            level="error",
            user=user,
            message=f"Abruf eingehender E-Mails fehlgeschlagen ({account.imap_host}:{account.imap_port})",
            detail=str(exc),
        )
        return []

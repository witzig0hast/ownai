import asyncio
import smtplib
import socket
from email.message import EmailMessage

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
    phase = "connect"
    try:
        with _IPv4SMTP(config.host, config.port, timeout=60, local_hostname="ownai-backend") as smtp:
            if config.use_tls:
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

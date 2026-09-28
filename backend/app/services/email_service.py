import asyncio
import smtplib
import socket
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import EmailAccount, User
from app.errors import APIError
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


def _send_sync(config: _EffectiveConfig, to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = config.from_address
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with _IPv4SMTP(config.host, config.port, timeout=15) as smtp:
        if config.use_tls:
            smtp.starttls()
        if config.username and config.password:
            smtp.login(config.username, config.password)
        smtp.send_message(message)


async def send_email(db: AsyncSession, user: User, to: str, subject: str, body: str) -> None:
    config = await effective_config(db, user)
    if config is None:
        raise EmailNotConfigured()
    try:
        # smtplib is blocking I/O - runs in a worker thread so it doesn't stall the event loop.
        await asyncio.to_thread(_send_sync, config, to, subject, body)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendFailed(f"E-Mail konnte nicht gesendet werden: {exc}") from exc

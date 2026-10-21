import asyncio
import socket
import time
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services import push_service, scheduler, sso_service, tts_service

Status = Literal["ok", "error", "not_configured"]

CHECK_TIMEOUT_SECONDS = 5.0


class DependencyStatus(BaseModel):
    key: str
    label: str
    status: Status
    detail: str | None = None
    # False means OwnAI doesn't work at all without it (DB, LLM); True means only one feature
    # is affected (voice, TTS, push, ...).
    optional: bool
    latency_ms: int | None = None


def _ollama_has_model(available: list[str], wanted: str) -> bool:
    # Ollama reports "nomic-embed-text:latest" for a model pulled as "nomic-embed-text".
    candidates = {wanted} if ":" in wanted else {wanted, f"{wanted}:latest"}
    return any(name in candidates for name in available)


async def _check_database(db: AsyncSession) -> tuple[Status, str | None]:
    await db.execute(text("SELECT 1"))
    return "ok", None


def _ollama_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=get_settings().ollama_base_url, timeout=CHECK_TIMEOUT_SECONDS)


async def _check_ollama() -> tuple[Status, str | None]:
    settings = get_settings()
    async with _ollama_client() as client:
        response = await client.get("/api/tags")
        response.raise_for_status()
    available = [m.get("name", "") for m in response.json().get("models", [])]

    wanted = [settings.ollama_chat_model, settings.ollama_embed_model]
    if settings.ollama_vision_model:
        wanted.append(settings.ollama_vision_model)
    if settings.ollama_title_model:
        wanted.append(settings.ollama_title_model)
    missing = [m for m in wanted if not _ollama_has_model(available, m)]
    if missing:
        commands = ", ".join(f"ollama pull {m}" for m in missing)
        return "error", f"Erreichbar, aber Modell fehlt: {commands}"
    return "ok", f"Chat-Modell: {settings.ollama_chat_model}"


async def _tcp_reachable(host: str, port: int) -> None:
    # IPv4 only, for the same reason as email_service._connect_ipv4.
    _reader, writer = await asyncio.open_connection(host, port, family=socket.AF_INET)
    writer.close()
    await writer.wait_closed()


async def _check_whisper() -> tuple[Status, str | None]:
    settings = get_settings()
    await _tcp_reachable(settings.whisper_host, settings.whisper_port)
    return "ok", f"{settings.whisper_host}:{settings.whisper_port}"


async def _check_tts() -> tuple[Status, str | None]:
    if not tts_service.is_configured():
        return "not_configured", "Vorlesen nutzt die Browser-Stimme (KOKORO_TTS_BASE_URL nicht gesetzt)."
    voices = await tts_service.list_voices()
    return "ok", f"{len(voices)} Stimme(n) verfügbar"


async def _check_smtp() -> tuple[Status, str | None]:
    settings = get_settings()
    if not settings.system_smtp_host:
        return "not_configured", "Kein System-Postfach - nur Nutzer mit eigenem SMTP-Konto können Mails senden."
    await _tcp_reachable(settings.system_smtp_host, settings.system_smtp_port)
    return "ok", f"{settings.system_smtp_host}:{settings.system_smtp_port}"


async def _check_push() -> tuple[Status, str | None]:
    if not push_service.is_push_configured():
        return "not_configured", "VAPID-Schlüssel fehlen (VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY)."
    return "ok", None


async def _check_sso() -> tuple[Status, str | None]:
    if not sso_service.is_configured():
        return "not_configured", None
    discovery = await sso_service._discovery_document()
    return "ok", discovery.get("issuer")


async def _check_scheduler() -> tuple[Status, str | None]:
    if scheduler.is_running():
        return "ok", None
    return "error", "Hintergrund-Jobs (Timer, Erinnerungen, Automationen, Agenten) laufen nicht."


async def _run(
    key: str, label: str, optional: bool, check: Callable[[], Awaitable[tuple[Status, str | None]]]
) -> DependencyStatus:
    started = time.monotonic()
    try:
        status, detail = await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS + 1)
    except TimeoutError:
        status, detail = "error", "Zeitüberschreitung - keine Antwort."
    except Exception as exc:  # noqa: BLE001 - any failure of a dependency is a status, not a crash
        status, detail = "error", str(exc) or exc.__class__.__name__
    latency = int((time.monotonic() - started) * 1000) if status == "ok" else None
    return DependencyStatus(key=key, label=label, status=status, detail=detail, optional=optional, latency_ms=latency)


async def collect(db: AsyncSession) -> list[DependencyStatus]:
    # The DB check runs first and on its own: AsyncSession isn't safe for concurrent use, and
    # every other check is independent network I/O that can run in parallel.
    database = await _run("database", "Datenbank", False, lambda: _check_database(db))
    others = await asyncio.gather(
        _run("ollama", "Sprachmodell (Ollama)", False, _check_ollama),
        _run("scheduler", "Hintergrund-Jobs", False, _check_scheduler),
        _run("whisper", "Spracherkennung (Whisper)", True, _check_whisper),
        _run("tts", "Sprachausgabe (Kokoro)", True, _check_tts),
        _run("smtp", "System-E-Mail (SMTP)", True, _check_smtp),
        _run("push", "Push-Benachrichtigungen", True, _check_push),
        _run("sso", "Single Sign-On", True, _check_sso),
    )
    return [database, *others]

import asyncio
import socket

import pytest
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioStop
from wyoming.event import Event
from wyoming.server import AsyncEventHandler, AsyncServer

from app.services import whisper_client


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _RecordingHandler(AsyncEventHandler):
    """Mock Wyoming ASR server: records the events it receives, replies with a canned transcript."""

    received: list[Event] = []  # class-level so the test can inspect it after the client disconnects

    async def handle_event(self, event: Event) -> bool:
        _RecordingHandler.received.append(event)
        if AudioStop.is_type(event.type):
            await self.write_event(Transcript(text="hallo welt").event())
            return False  # close the connection after responding, like a real ASR server would
        return True


async def _run_server_once(port: int) -> None:
    server = AsyncServer.from_uri(f"tcp://127.0.0.1:{port}")
    await server.run(_RecordingHandler)


@pytest.mark.asyncio
async def test_transcribe_round_trip(monkeypatch):
    port = _free_port()
    _RecordingHandler.received = []

    server_task = asyncio.create_task(_run_server_once(port))
    await asyncio.sleep(0.2)  # let the server start listening

    settings = whisper_client.get_settings()
    monkeypatch.setattr(settings, "whisper_host", "127.0.0.1")
    monkeypatch.setattr(settings, "whisper_port", port)

    async def fake_decode(_audio_bytes: bytes) -> bytes:
        return b"\x00\x01" * 8000  # stand-in PCM, ffmpeg itself is exercised separately

    monkeypatch.setattr(whisper_client, "_decode_to_pcm", fake_decode)

    text = await whisper_client.transcribe(b"fake-encoded-audio", language="de")

    assert text == "hallo welt"

    server_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await server_task

    types = [e.type for e in _RecordingHandler.received]
    assert types[0] == "transcribe"
    assert types[1] == "audio-start"
    assert "audio-chunk" in types
    assert types[-1] == "audio-stop"

    transcribe_event = Transcribe.from_event(_RecordingHandler.received[0])
    assert transcribe_event.language == "de"


@pytest.mark.asyncio
async def test_transcribe_raises_on_unreachable_server(monkeypatch):
    settings = whisper_client.get_settings()
    monkeypatch.setattr(settings, "whisper_host", "127.0.0.1")
    monkeypatch.setattr(settings, "whisper_port", _free_port())  # nothing listening here

    async def fake_decode(_audio_bytes: bytes) -> bytes:
        return b"\x00\x00" * 100

    monkeypatch.setattr(whisper_client, "_decode_to_pcm", fake_decode)

    with pytest.raises(whisper_client.WhisperError):
        await whisper_client.transcribe(b"fake-encoded-audio")


@pytest.mark.asyncio
async def test_decode_to_pcm_uses_real_ffmpeg():
    """Exercises the real ffmpeg subprocess path (not mocked) against a tiny generated tone,
    to catch ffmpeg-invocation mistakes the mocked round-trip test above can't see."""
    import subprocess

    webm_bytes = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.2",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "libopus",
            "-f",
            "webm",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout

    pcm = await whisper_client._decode_to_pcm(webm_bytes)

    assert len(pcm) > 0
    assert len(pcm) % 2 == 0  # 16-bit samples

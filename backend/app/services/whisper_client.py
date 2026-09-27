import asyncio

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient

from app.config import get_settings

# Wyoming's own audio convention: 16-bit signed little-endian PCM, mono, 16 kHz.
_PCM_RATE = 16000
_PCM_WIDTH = 2  # bytes per sample (16-bit)
_PCM_CHANNELS = 1
_CHUNK_BYTES = 4096  # arbitrary, small enough to stream without huge single writes

_MAX_EVENTS_WITHOUT_TRANSCRIPT = 50  # safety bound against a misbehaving/chatty server


class WhisperError(Exception):
    pass


async def _decode_to_pcm(audio_bytes: bytes) -> bytes:
    """Uses ffmpeg to decode arbitrary client-recorded audio (webm/opus, mp4/aac, wav, ...)
    into raw 16 kHz mono 16-bit PCM, the format the Wyoming protocol expects.
    """
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-ar",
        str(_PCM_RATE),
        "-ac",
        str(_PCM_CHANNELS),
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate(audio_bytes)
    if process.returncode != 0:
        raise WhisperError(f"Audio-Dekodierung fehlgeschlagen: {stderr.decode(errors='replace').strip()}")
    return stdout


async def transcribe(audio_bytes: bytes, language: str | None = None) -> str:
    """Sends audio to the configured Wyoming ASR server (e.g. wyoming-whisper) and returns the transcript."""
    settings = get_settings()
    pcm = await _decode_to_pcm(audio_bytes)
    if not pcm:
        raise WhisperError("Leeres oder nicht dekodierbares Audio.")

    try:
        async with AsyncTcpClient(
            settings.whisper_host, settings.whisper_port, connect_timeout=5.0, read_timeout=30.0
        ) as client:
            await client.write_event(Transcribe(language=language or settings.whisper_language).event())
            await client.write_event(AudioStart(rate=_PCM_RATE, width=_PCM_WIDTH, channels=_PCM_CHANNELS).event())

            for offset in range(0, len(pcm), _CHUNK_BYTES):
                chunk = pcm[offset : offset + _CHUNK_BYTES]
                await client.write_event(
                    AudioChunk(rate=_PCM_RATE, width=_PCM_WIDTH, channels=_PCM_CHANNELS, audio=chunk).event()
                )

            await client.write_event(AudioStop().event())

            for _ in range(_MAX_EVENTS_WITHOUT_TRANSCRIPT):
                event = await client.read_event()
                if event is None:
                    raise WhisperError("Verbindung zum Whisper-Server wurde unerwartet beendet.")
                if Transcript.is_type(event.type):
                    return Transcript.from_event(event).text
            raise WhisperError("Whisper-Server hat kein Transkript zurückgegeben.")
    except (OSError, asyncio.TimeoutError) as exc:
        raise WhisperError(f"Whisper-Server nicht erreichbar: {exc}") from exc

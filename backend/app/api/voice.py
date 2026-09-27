from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.errors import APIError
from app.schemas.voice import VoiceTranscribeResponse
from app.services import whisper_client

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB — generous for a voice message, guards against abuse


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    audio: UploadFile = File(...),
    _user: User = Depends(get_current_user),
) -> VoiceTranscribeResponse:
    audio_bytes = await audio.read(MAX_UPLOAD_BYTES + 1)
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        raise APIError(413, "audio_too_large", "Audio-Datei ist zu groß (max. 25 MB).")
    if not audio_bytes:
        raise APIError(400, "empty_audio", "Keine Audiodaten empfangen.")

    try:
        text = await whisper_client.transcribe(audio_bytes)
    except whisper_client.WhisperError as exc:
        raise APIError(502, "whisper_unavailable", str(exc)) from exc

    return VoiceTranscribeResponse(text=text)

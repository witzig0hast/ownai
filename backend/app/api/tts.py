from fastapi import APIRouter, Depends, Response

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.errors import TTSNotConfigured, TTSUnavailable
from app.schemas.tts import TTSSpeakIn, TTSVoicesOut
from app.services import tts_service

router = APIRouter(prefix="/tts", tags=["tts"])

# Guards against a pathologically long reply choking the TTS server - well beyond any real
# assistant reply, just a sanity bound.
MAX_TEXT_CHARS = 4000


@router.get("/voices", response_model=TTSVoicesOut)
async def list_voices(_user: User = Depends(get_current_user)) -> TTSVoicesOut:
    """Empty list (not an error) when no TTS server is configured - the client falls back to
    browser voices in that case, see web/src/lib/tts.ts."""
    return TTSVoicesOut(voices=await tts_service.list_voices())


@router.post("/speak")
async def speak(body: TTSSpeakIn, _user: User = Depends(get_current_user)) -> Response:
    text = body.text.strip()
    if not text:
        return Response(status_code=204)
    if not tts_service.is_configured():
        raise TTSNotConfigured()

    try:
        audio = await tts_service.synthesize(text[:MAX_TEXT_CHARS], voice=body.voice)
    except tts_service.TTSError as exc:
        raise TTSUnavailable(str(exc)) from exc

    return Response(content=audio, media_type="audio/mpeg")

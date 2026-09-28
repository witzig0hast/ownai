from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.schemas.clipper import ClipOut, ClipRequest
from app.services import clipper_service

router = APIRouter(tags=["clipper"])


@router.post("/clip", response_model=ClipOut)
async def clip_url(payload: ClipRequest, _user: User = Depends(get_current_user)) -> ClipOut:
    result = await clipper_service.clip(payload.url)
    return ClipOut(**result)

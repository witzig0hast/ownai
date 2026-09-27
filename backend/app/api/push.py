from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.push import PushSubscribeRequest, PushUnsubscribeRequest, VapidPublicKeyOut
from app.services import push_service

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyOut)
async def get_vapid_public_key() -> VapidPublicKeyOut:
    settings = get_settings()
    return VapidPublicKeyOut(
        public_key=settings.vapid_public_key, configured=push_service.is_push_configured()
    )


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe(
    payload: PushSubscribeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await push_service.add_subscription(
        db, user, endpoint=payload.endpoint, p256dh=payload.keys.p256dh, auth=payload.keys.auth
    )


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    payload: PushUnsubscribeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await push_service.remove_subscription(db, user, payload.endpoint)

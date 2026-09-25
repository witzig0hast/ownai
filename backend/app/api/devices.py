from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.security import generate_device_api_key
from app.db.models import Device, User
from app.db.session import get_db
from app.schemas.devices import DeviceOut, DeviceRegisterRequest

router = APIRouter(tags=["devices"])


@router.post("/devices/register", response_model=DeviceOut, status_code=201)
async def register_device(
    payload: DeviceRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceOut:
    raw_key, key_hash = generate_device_api_key()
    device = Device(
        user_id=user.id,
        platform=payload.platform,
        label=payload.label,
        push_token=payload.push_token,
        api_key_hash=key_hash,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return DeviceOut(id=device.id, platform=device.platform, device_api_key=raw_key, label=device.label)

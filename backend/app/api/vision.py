import asyncio

from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.errors import APIError
from app.schemas.vision import VisionDescribeResponse
from app.services import vision_service

router = APIRouter(prefix="/vision", tags=["vision"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB — generous for a photo, guards against abuse


@router.post("/describe", response_model=VisionDescribeResponse)
async def describe_image(
    image: UploadFile = File(...),
    _user: User = Depends(get_current_user),
) -> VisionDescribeResponse:
    image_bytes = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise APIError(413, "image_too_large", "Bild ist zu groß (max. 15 MB).")
    if not image_bytes:
        raise APIError(400, "empty_image", "Keine Bilddaten empfangen.")

    # ocr_image is synchronous, CPU-bound Tesseract work - run it off the event loop. The
    # backend runs as a single Uvicorn worker (see README.md), so calling it directly here would
    # stall every other concurrent request (any user, any endpoint) for the OCR's full duration.
    ocr_text = await asyncio.to_thread(vision_service.ocr_image, image_bytes)
    description = await vision_service.describe_image(image_bytes)
    return VisionDescribeResponse(ocr_text=ocr_text, description=description)

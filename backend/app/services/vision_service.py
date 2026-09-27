import base64
import io
import logging

import httpx
import pytesseract
from PIL import Image, UnidentifiedImageError

from app.config import get_settings

logger = logging.getLogger(__name__)


def ocr_image(image_bytes: bytes) -> str | None:
    """Extracts text from an image via Tesseract OCR - deterministic, no LLM/network call, works
    regardless of whether a vision model is configured (see describe_image below). Best-effort:
    returns None (not an error) on any failure - a bad/corrupt image or a missing tesseract
    binary shouldn't break the upload, just mean no OCR text came back."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang="deu+eng")
    except UnidentifiedImageError:
        return None
    except pytesseract.TesseractNotFoundError:
        logger.warning("OCR skipped: tesseract binary not found (see Dockerfile's tesseract-ocr package)")
        return None
    except Exception:  # noqa: BLE001 - OCR is best-effort, any failure just means no text
        logger.exception("OCR failed unexpectedly")
        return None
    return text.strip() or None


async def describe_image(image_bytes: bytes) -> str | None:
    """Asks a vision-capable Ollama model (OLLAMA_VISION_MODEL) to describe the image. Returns
    None, not an error, when no vision model is configured - OCR alone is still useful without
    one, so this is an optional enhancement, not a requirement."""
    settings = get_settings()
    if not settings.ollama_vision_model:
        return None

    encoded = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": settings.ollama_vision_model,
        "messages": [
            {
                "role": "user",
                "content": "Beschreibe kurz und präzise, was auf diesem Bild zu sehen ist, auf Deutsch.",
                "images": [encoded],
            }
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=60.0) as client:
        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError:
            logger.warning("Vision model description failed (Ollama unreachable or model not pulled)")
            return None

    data = response.json()
    content = (data.get("message") or {}).get("content")
    return content.strip() if content else None

import asyncio
import time

from httpx import AsyncClient

from app.services import vision_service


async def test_describe_image_returns_ocr_and_description(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr(vision_service, "ocr_image", lambda image_bytes: "Erkannter Text")  # noqa: ARG005

    async def fake_describe(image_bytes):  # noqa: ARG001
        return "Ein Foto von einer Katze."

    monkeypatch.setattr(vision_service, "describe_image", fake_describe)

    response = await client.post(
        "/vision/describe",
        files={"image": ("katze.png", b"fake-image-bytes", "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"ocr_text": "Erkannter Text", "description": "Ein Foto von einer Katze."}


async def test_describe_image_ocr_none_when_unavailable(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr(vision_service, "ocr_image", lambda image_bytes: None)  # noqa: ARG005

    async def fake_describe(image_bytes):  # noqa: ARG001
        return None

    monkeypatch.setattr(vision_service, "describe_image", fake_describe)

    response = await client.post(
        "/vision/describe",
        files={"image": ("bild.png", b"fake-image-bytes", "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"ocr_text": None, "description": None}


async def test_describe_image_rejects_empty_upload(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/vision/describe",
        files={"image": ("leer.png", b"", "image/png")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_image"


def test_ocr_image_returns_none_on_unidentifiable_bytes():
    assert vision_service.ocr_image(b"not-an-image") is None


async def test_ocr_runs_off_the_event_loop_so_other_requests_are_not_blocked(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """ocr_image is synchronous, CPU-bound Tesseract work. Calling it directly inside the async
    route would freeze the event loop for its whole duration - on this backend's single Uvicorn
    worker (see README.md), that stalls every other concurrent request too, for any user, on any
    endpoint. Running it via asyncio.to_thread fixes that: an unrelated, trivial request made
    concurrently with a "slow" OCR call must not be held up by it."""

    def slow_ocr(image_bytes):  # noqa: ARG001
        time.sleep(0.4)
        return "Text"

    monkeypatch.setattr(vision_service, "ocr_image", slow_ocr)

    async def fake_describe(image_bytes):  # noqa: ARG001
        return None

    monkeypatch.setattr(vision_service, "describe_image", fake_describe)

    async def describe_call():
        return await client.post(
            "/vision/describe",
            files={"image": ("bild.png", b"fake-image-bytes", "image/png")},
            headers=auth_headers,
        )

    async def unrelated_call():
        start = time.monotonic()
        response = await client.get("/chat/conversations", headers=auth_headers)
        return response, time.monotonic() - start

    _, (unrelated_response, unrelated_elapsed) = await asyncio.gather(describe_call(), unrelated_call())
    assert unrelated_response.status_code == 200
    # If OCR still blocked the event loop, this would have had to wait out (most of) the 0.4s
    # sleep too - it should instead return almost immediately.
    assert unrelated_elapsed < 0.3

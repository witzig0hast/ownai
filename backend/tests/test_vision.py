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

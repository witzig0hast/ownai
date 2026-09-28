from bs4 import BeautifulSoup
import httpx

from app.errors import APIError

MAX_TEXT_LENGTH = 5000
# Tags whose content is never article text - stripped before extracting readable text.
_NOISE_TAGS = ("script", "style", "nav", "header", "footer", "aside", "form", "noscript")


class ClipError(APIError):
    def __init__(self, message: str):
        super().__init__(502, "clip_error", message)


def _client() -> httpx.AsyncClient:
    """Separate factory purely so tests can monkeypatch it - same pattern as
    home_assistant_service._client / weather_service._client / searxng_service._client."""
    return httpx.AsyncClient(timeout=15.0, follow_redirects=True)


async def clip(url: str) -> dict[str, str]:
    async with _client() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ClipError(f"Seite nicht erreichbar: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and not response.text.lstrip().startswith("<"):
        # Not HTML (e.g. a plain-text or JSON URL) - just use the raw body as-is.
        text = response.text.strip()
        title = url
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()
        title = soup.title.get_text(strip=True) if soup.title else url
        text = soup.get_text(separator="\n", strip=True)

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "…"
    if not text:
        raise ClipError("Seite enthält keinen lesbaren Text.")

    return {"title": title, "url": url, "text": text}

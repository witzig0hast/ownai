from typing import Any

import httpx

from app.config import get_settings


class OllamaError(Exception):
    pass


async def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Calls Ollama's native /api/chat (non-streaming) and returns the response `message` dict.

    Response message shape: {"role": "assistant", "content": str, "tool_calls": [{"function": {"name", "arguments"}}] | None}
    `arguments` on a tool call is already a dict (Ollama, unlike OpenAI, does not JSON-encode it as a string).
    """
    settings = get_settings()
    payload: dict[str, Any] = {
        "model": settings.ollama_chat_model,
        "messages": messages,
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0) as client:
        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

    data = response.json()
    message = data.get("message")
    if message is None:
        raise OllamaError(f"Unexpected Ollama response, no 'message' field: {data}")
    return message


async def warmup() -> None:
    """Loads the model into (V)RAM without generating anything, so the first real reply doesn't
    pay for the load time - Ollama's documented trick for this is a /api/chat call with an empty
    `messages` list. Best-effort: any failure here shouldn't block the page that triggered it."""
    settings = get_settings()
    payload = {
        "model": settings.ollama_chat_model,
        "messages": [],
        "keep_alive": settings.ollama_keep_alive,
    }
    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0) as client:
        try:
            await client.post("/api/chat", json=payload)
        except httpx.HTTPError:
            pass


async def generate_title(user_message: str, assistant_reply: str) -> str | None:
    """Generates a short conversation title from its first exchange - reuses the main chat model
    by default (a dedicated smaller one buys little here: Hermes3 8B and a small Llama are similar
    sizes, and it's the short *output* that's fast, not the model). Set OLLAMA_TITLE_MODEL to point
    this at a separate, genuinely smaller model instead, if one is pulled on the Ollama instance.
    Best-effort: returns None on any failure so a title just stays unset rather than blocking.
    """
    settings = get_settings()
    model = settings.ollama_title_model or settings.ollama_chat_model
    prompt = (
        "Fasse den folgenden Gesprächsanfang in einem sehr kurzen Titel zusammen (maximal 5 Wörter, "
        "keine Anführungszeichen, kein Punkt am Ende, keine Erklärung). Antworte NUR mit dem Titel."
        f"\n\nNutzer: {user_message}\nAssistent: {assistant_reply}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"num_predict": 20},
    }
    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=30.0) as client:
        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError:
            return None

    data = response.json()
    content = ((data.get("message") or {}).get("content") or "").strip().strip("\"'").strip()
    return content[:100] or None


async def is_reachable() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=3.0) as client:
            response = await client.get("/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False

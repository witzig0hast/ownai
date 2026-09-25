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


async def is_reachable() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=3.0) as client:
            response = await client.get("/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False

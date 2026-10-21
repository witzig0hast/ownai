import httpx
from httpx import AsyncClient

from app.config import get_settings
from app.services import system_status_service


def _by_key(response) -> dict[str, dict]:
    return {d["key"]: d for d in response.json()["dependencies"]}


async def test_system_status_requires_auth(client: AsyncClient):
    response = await client.get("/admin/system-status")
    assert response.status_code == 401


async def test_system_status_reports_every_dependency(client: AsyncClient, auth_headers: dict):
    response = await client.get("/admin/system-status", headers=auth_headers)
    assert response.status_code == 200
    deps = _by_key(response)

    assert set(deps) == {"database", "ollama", "scheduler", "whisper", "tts", "smtp", "push", "sso"}
    assert deps["database"]["status"] == "ok"
    assert deps["database"]["optional"] is False
    # Test env points Ollama at an unresolvable host - must be reported, not crash the endpoint.
    assert deps["ollama"]["status"] == "error"
    assert deps["ollama"]["detail"]
    # Unset optional integrations are "not_configured", not "error".
    assert deps["tts"]["status"] == "not_configured"
    assert deps["sso"]["status"] == "not_configured"


def _fake_ollama(monkeypatch, model_names: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": n} for n in model_names]})

    def fake_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url="http://ollama.test", transport=httpx.MockTransport(handler))

    monkeypatch.setattr(system_status_service, "_ollama_client", fake_client)


async def test_ollama_check_flags_missing_model_with_pull_command(monkeypatch):
    settings = get_settings()
    _fake_ollama(monkeypatch, [settings.ollama_chat_model])

    status, detail = await system_status_service._check_ollama()

    assert status == "error"
    assert f"ollama pull {settings.ollama_embed_model}" in detail


async def test_ollama_check_accepts_latest_tag(monkeypatch):
    settings = get_settings()
    _fake_ollama(monkeypatch, [settings.ollama_chat_model, f"{settings.ollama_embed_model}:latest"])

    status, _detail = await system_status_service._check_ollama()

    assert status == "ok"


async def test_a_hanging_check_becomes_a_timeout_error(monkeypatch):
    import asyncio

    monkeypatch.setattr(system_status_service, "CHECK_TIMEOUT_SECONDS", 0.05)

    async def never_returns():
        await asyncio.sleep(10)

    result = await system_status_service._run("x", "X", True, never_returns)
    assert result.status == "error"
    assert "Zeitüberschreitung" in result.detail

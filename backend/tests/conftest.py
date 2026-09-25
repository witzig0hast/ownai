import os
import tempfile

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp_db_path}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-use"
os.environ["OLLAMA_BASE_URL"] = "http://ollama.invalid"

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac


@pytest_asyncio.fixture
async def registered_user_tokens(client: AsyncClient) -> dict:
    await client.post(
        "/auth/register",
        json={"email": "karim@example.com", "password": "s3cure-password", "display_name": "Karim"},
    )
    response = await client.post("/auth/login", json={"email": "karim@example.com", "password": "s3cure-password"})
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(registered_user_tokens: dict) -> dict:
    return {"Authorization": f"Bearer {registered_user_tokens['access_token']}"}

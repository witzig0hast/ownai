from httpx import AsyncClient


async def test_register_login_and_me(client: AsyncClient):
    register = await client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "s3cure-password", "display_name": "A"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "a@example.com"

    login = await client.post("/auth/login", json={"email": "a@example.com", "password": "s3cure-password"})
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["display_name"] == "A"


async def test_register_duplicate_email_conflicts(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "s3cure-password", "display_name": "Dup"}
    first = await client.post("/auth/register", json=payload)
    second = await client.post("/auth/register", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_taken"


async def test_login_wrong_password_is_rejected(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "b@example.com", "password": "s3cure-password", "display_name": "B"},
    )
    response = await client.post("/auth/login", json={"email": "b@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_refresh_rotates_token_and_old_one_stops_working(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "c@example.com", "password": "s3cure-password", "display_name": "C"},
    )
    login = await client.post("/auth/login", json={"email": "c@example.com", "password": "s3cure-password"})
    old_refresh = login.json()["refresh_token"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != old_refresh  # each refresh token has a unique jti

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
    assert me.status_code == 200

    reused = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "invalid_refresh_token"


async def test_me_requires_authentication(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"

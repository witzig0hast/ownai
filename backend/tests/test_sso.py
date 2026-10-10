import logging
from urllib.parse import parse_qs, urlparse

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from app.auth.security import create_sso_state_token
from app.config import get_settings
from app.services import sso_service


def _configure_sso(monkeypatch, **overrides):
    settings = get_settings()
    monkeypatch.setattr(settings, "oidc_issuer_url", "https://auth.example.com")
    monkeypatch.setattr(settings, "oidc_client_id", "ownai-client")
    monkeypatch.setattr(settings, "oidc_client_secret", "s3cret")
    monkeypatch.setattr(settings, "oidc_redirect_uri", "https://ownai.example.com/api/v1/auth/sso/callback")
    monkeypatch.setattr(settings, "oidc_frontend_callback_url", "https://ownai.example.com/sso-callback")
    for key, value in overrides.items():
        monkeypatch.setattr(settings, key, value)


def _generate_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


TEST_KID = "test-key-1"


def _sign_id_token(private_key, **claim_overrides) -> str:
    claims = {
        "sub": "oidc-subject-123",
        "email": "karim@example.com",
        "name": "Karim",
        "aud": "ownai-client",
        "iss": "https://auth.example.com",
        "nonce": "the-nonce",
    }
    claims.update(claim_overrides)
    return pyjwt.encode(claims, private_key, algorithm="RS256", headers={"kid": TEST_KID})


def _build_jwks(public_key) -> dict:
    """A JWKS document (see sso_service._fetch_jwks's return shape) containing just the one
    public key, built the same way a real OIDC provider's own JWKS endpoint would describe it."""
    jwk_dict = pyjwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk_dict["kid"] = TEST_KID
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    return {"keys": [jwk_dict]}


def test_verify_id_token_accepts_a_validly_signed_token(monkeypatch):
    _configure_sso(monkeypatch)
    private_key, public_key = _generate_rsa_keypair()

    token = _sign_id_token(private_key)
    claims = sso_service._verify_id_token(token, _build_jwks(public_key))

    assert claims["sub"] == "oidc-subject-123"
    assert claims["email"] == "karim@example.com"


def test_verify_id_token_rejects_wrong_audience(monkeypatch):
    _configure_sso(monkeypatch)
    private_key, public_key = _generate_rsa_keypair()

    token = _sign_id_token(private_key, aud="someone-elses-client")
    with pytest.raises(pyjwt.PyJWTError):
        sso_service._verify_id_token(token, _build_jwks(public_key))


def test_verify_id_token_rejects_wrong_issuer(monkeypatch):
    _configure_sso(monkeypatch)
    private_key, public_key = _generate_rsa_keypair()

    token = _sign_id_token(private_key, iss="https://not-my-provider.example.com")
    with pytest.raises(pyjwt.PyJWTError):
        sso_service._verify_id_token(token, _build_jwks(public_key))


def test_verify_id_token_rejects_signature_from_a_different_key(monkeypatch):
    _configure_sso(monkeypatch)
    _, real_public_key = _generate_rsa_keypair()
    attacker_private_key, _ = _generate_rsa_keypair()

    forged_token = _sign_id_token(attacker_private_key)
    with pytest.raises(pyjwt.PyJWTError):
        sso_service._verify_id_token(forged_token, _build_jwks(real_public_key))


def test_verify_id_token_rejects_unknown_kid(monkeypatch):
    """No key in the JWKS matches the token's kid, and there's more than one key to guess from -
    must be a clear SsoError, not an obscure KeyError/AttributeError."""
    _configure_sso(monkeypatch)
    private_key, public_key = _generate_rsa_keypair()
    _, other_public_key = _generate_rsa_keypair()

    jwks = _build_jwks(public_key)
    other_jwk = pyjwt.algorithms.RSAAlgorithm.to_jwk(other_public_key, as_dict=True)
    other_jwk["kid"] = "a-different-key"
    jwks["keys"].append(other_jwk)

    token = pyjwt.encode(
        {
            "sub": "oidc-subject-123",
            "email": "karim@example.com",
            "aud": "ownai-client",
            "iss": "https://auth.example.com",
            "nonce": "the-nonce",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "yet-another-unknown-key"},
    )

    with pytest.raises(sso_service.SsoError):
        sso_service._verify_id_token(token, jwks)


async def test_sso_status_reflects_configuration(client: AsyncClient, monkeypatch):
    response = await client.get("/auth/sso/status")
    assert response.json() == {"enabled": False}

    _configure_sso(monkeypatch)
    response = await client.get("/auth/sso/status")
    assert response.json() == {"enabled": True}


async def test_sso_login_returns_404_when_not_configured(client: AsyncClient):
    response = await client.get("/auth/sso/login")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sso_not_configured"


async def test_sso_login_redirects_to_provider_with_state_and_nonce(client: AsyncClient, monkeypatch):
    _configure_sso(monkeypatch)

    async def fake_discovery():
        return {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/jwks",
        }

    monkeypatch.setattr(sso_service, "_discovery_document", fake_discovery)

    response = await client.get("/auth/sso/login")
    assert response.status_code == 307
    location = urlparse(response.headers["location"])
    assert location.netloc == "auth.example.com"
    assert location.path == "/authorize"
    params = parse_qs(location.query)
    assert params["client_id"] == ["ownai-client"]
    assert params["response_type"] == ["code"]
    assert "state" in params
    assert "nonce" in params


async def test_sso_callback_rejects_invalid_state(client: AsyncClient, monkeypatch):
    _configure_sso(monkeypatch)
    response = await client.get("/auth/sso/callback", params={"code": "abc", "state": "not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_sso_state"


async def test_sso_callback_bootstraps_first_user_as_admin(client: AsyncClient, monkeypatch):
    _configure_sso(monkeypatch)
    state = create_sso_state_token("the-nonce")

    async def fake_exchange(code, *, nonce):  # noqa: ARG001
        assert nonce == "the-nonce"
        return {"sub": "oidc-subject-123", "email": "karim@example.com", "name": "Karim"}

    monkeypatch.setattr(sso_service, "exchange_code_for_claims", fake_exchange)

    response = await client.get("/auth/sso/callback", params={"code": "abc", "state": state})
    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://ownai.example.com/sso-callback#")
    fragment = urlparse(location).fragment
    params = parse_qs(fragment)
    assert "access_token" in params
    assert "refresh_token" in params

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {params['access_token'][0]}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "karim@example.com"
    assert body["is_admin"] is True
    assert body["approval_status"] == "approved"


async def test_sso_callback_second_user_starts_pending(client: AsyncClient, auth_headers: dict, monkeypatch):
    # auth_headers registers the first (admin) user via the normal password flow.
    _configure_sso(monkeypatch)
    state = create_sso_state_token("the-nonce")

    async def fake_exchange(code, *, nonce):  # noqa: ARG001
        return {"sub": "oidc-subject-456", "email": "other@example.com", "name": "Other"}

    monkeypatch.setattr(sso_service, "exchange_code_for_claims", fake_exchange)

    response = await client.get("/auth/sso/callback", params={"code": "abc", "state": state})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "registration_pending"

    pending = await client.get("/admin/users/pending", headers=auth_headers)
    assert any(u["email"] == "other@example.com" for u in pending.json()["users"])


async def test_sso_callback_links_existing_password_account_by_email(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    _configure_sso(monkeypatch)
    state = create_sso_state_token("the-nonce")

    async def fake_exchange(code, *, nonce):  # noqa: ARG001
        return {"sub": "oidc-subject-123", "email": "karim@example.com", "name": "Karim"}

    monkeypatch.setattr(sso_service, "exchange_code_for_claims", fake_exchange)

    response = await client.get("/auth/sso/callback", params={"code": "abc", "state": state})
    assert response.status_code == 307
    fragment = urlparse(response.headers["location"]).fragment
    access_token = parse_qs(fragment)["access_token"][0]

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    # auth_headers' bootstrap user is karim@example.com (see conftest.py) - this must be the
    # SAME account (admin, approved), not a second one created from the SSO claims.
    assert me.json()["is_admin"] is True
    assert me.json()["approval_status"] == "approved"

    users = await client.get("/admin/users", headers=auth_headers)
    assert len(users.json()["users"]) == 1


async def test_sso_callback_respects_registration_closed(client: AsyncClient, auth_headers: dict, monkeypatch):
    _configure_sso(monkeypatch)
    await client.patch("/admin/settings", json={"registration_open": False}, headers=auth_headers)

    state = create_sso_state_token("the-nonce")

    async def fake_exchange(code, *, nonce):  # noqa: ARG001
        return {"sub": "oidc-subject-456", "email": "newcomer@example.com", "name": "Newcomer"}

    monkeypatch.setattr(sso_service, "exchange_code_for_claims", fake_exchange)

    response = await client.get("/auth/sso/callback", params={"code": "abc", "state": state})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "registration_closed"


async def test_sso_callback_logs_sso_error_server_side(client: AsyncClient, monkeypatch, caplog):
    """A 5xx APIError like SsoError is otherwise only visible as a JSON body at the end of a
    browser redirect chain - app/main.py's api_error_handler must also log it, so the real cause
    (provider unreachable, bad id_token, ...) shows up directly in `docker compose logs backend`."""
    _configure_sso(monkeypatch)
    state = create_sso_state_token("the-nonce")

    async def fake_exchange(code, *, nonce):  # noqa: ARG001
        raise sso_service.SsoError("SSO-Provider nicht erreichbar: boom")

    monkeypatch.setattr(sso_service, "exchange_code_for_claims", fake_exchange)

    with caplog.at_level(logging.WARNING):
        response = await client.get("/auth/sso/callback", params={"code": "abc", "state": state})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "sso_error"
    assert any("SSO-Provider nicht erreichbar: boom" in record.message for record in caplog.records)


async def test_sso_callback_rejects_invalid_state_without_logging(client: AsyncClient, monkeypatch, caplog):
    """A 4xx APIError (wrong state, routine client error) must NOT trigger the 5xx-only warning
    log - that log exists specifically to surface unexpected server/dependency failures, not
    every ordinary rejection."""
    _configure_sso(monkeypatch)

    with caplog.at_level(logging.WARNING):
        response = await client.get("/auth/sso/callback", params={"code": "abc", "state": "not-a-real-token"})

    assert response.status_code == 401
    assert caplog.records == []

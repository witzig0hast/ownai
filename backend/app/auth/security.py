import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()

JWT_ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised for any invalid/expired/mistyped JWT."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _encode(claims: dict, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**claims, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _encode(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.access_token_ttl_minutes),
    )


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Returns (encoded_token, jti, expires_at). Caller persists a RefreshToken row keyed by jti."""
    jti = str(uuid.uuid4())
    ttl = timedelta(days=settings.refresh_token_ttl_days)
    expires_at = datetime.now(timezone.utc) + ttl
    token = _encode({"sub": user_id, "type": "refresh", "jti": jti}, ttl)
    return token, jti, expires_at


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"expected token type {expected_type!r}, got {payload.get('type')!r}")
    return payload


# SSO's `state` param (see app/services/sso_service.py) is this same self-signed JWT pattern
# instead of a server-side session/cookie store - this backend has none (pure bearer-token API)
# and adding one just for a single login flow isn't worth it. The provider hands `state` back
# unmodified on the callback, so verifying our own signature on it is equivalent to looking up a
# server-side record, without needing one.
SSO_STATE_TTL_MINUTES = 10


def create_sso_state_token(nonce: str, *, link_user_id: str | None = None) -> str:
    # link_user_id turns this into an "account linking" flow instead of a login: present, the
    # callback links the returned SSO identity to that already-authenticated user's existing
    # account instead of logging in as (or creating) a separate one - see app/api/sso.py.
    claims = {"type": "sso_state", "nonce": nonce}
    if link_user_id is not None:
        claims["link_user_id"] = link_user_id
    return _encode(claims, timedelta(minutes=SSO_STATE_TTL_MINUTES))


def decode_sso_state_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != "sso_state":
        raise TokenError("not an sso_state token")
    return payload


def _generate_prefixed_api_key(prefix: str) -> tuple[str, str]:
    """Returns (raw_key_shown_once, sha256_hash_to_store)."""
    raw_key = f"{prefix}_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, key_hash


def generate_device_api_key() -> tuple[str, str]:
    return _generate_prefixed_api_key("ownai_dk")


def hash_device_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_agent_api_key() -> tuple[str, str]:
    return _generate_prefixed_api_key("ownai_ak")


def hash_agent_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

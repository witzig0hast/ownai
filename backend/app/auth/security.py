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


def generate_device_api_key() -> tuple[str, str]:
    """Returns (raw_key_shown_once, sha256_hash_to_store)."""
    raw_key = f"ownai_dk_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, key_hash


def hash_device_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

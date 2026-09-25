from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    TokenError,
)
from app.config import get_settings
from app.db.models import RefreshToken, User
from app.db.session import get_db
from app.errors import EmailTaken, InvalidCredentials, InvalidRefreshToken
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserOut
from app.utils import ensure_utc

router = APIRouter(tags=["auth"])
settings = get_settings()


async def _issue_token_pair(db: AsyncSession, user_id: str) -> TokenPair:
    access_token = create_access_token(user_id)
    refresh_token, jti, expires_at = create_refresh_token(user_id)
    db.add(RefreshToken(id=jti, user_id=user_id, expires_at=expires_at))
    await db.commit()
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise EmailTaken()

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentials()
    return await _issue_token_pair(db, user.id)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise InvalidRefreshToken(str(exc)) from exc

    stored = await db.get(RefreshToken, claims["jti"])
    if stored is None or stored.revoked or ensure_utc(stored.expires_at) < datetime.now(timezone.utc):
        raise InvalidRefreshToken()

    # Rotate: revoke the used refresh token, issue a fresh pair.
    stored.revoked = True
    await db.commit()
    return await _issue_token_pair(db, claims["sub"])


@router.get("/users/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user

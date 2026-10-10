import secrets

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import _issue_token_pair
from app.auth.security import TokenError, create_sso_state_token, decode_sso_state_token
from app.config import get_settings
from app.db.session import get_db
from app.errors import InvalidSsoState, SsoNotConfigured
from app.services import sso_service

router = APIRouter(prefix="/auth/sso", tags=["auth"])


@router.get("/status")
async def sso_status() -> dict[str, bool]:
    """Unauthenticated on purpose - the login page needs this before anyone is logged in, to
    decide whether to show the "Mit SSO anmelden" button at all."""
    return {"enabled": sso_service.is_configured()}


@router.get("/login")
async def sso_login() -> RedirectResponse:
    if not sso_service.is_configured():
        raise SsoNotConfigured()
    nonce = secrets.token_urlsafe(16)
    state = create_sso_state_token(nonce)
    url = await sso_service.authorization_url(state=state, nonce=nonce)
    return RedirectResponse(url)


@router.get("/callback")
async def sso_callback(code: str, state: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    if not sso_service.is_configured():
        raise SsoNotConfigured()

    try:
        state_claims = decode_sso_state_token(state)
    except TokenError as exc:
        raise InvalidSsoState() from exc

    claims = await sso_service.exchange_code_for_claims(code, nonce=state_claims["nonce"])
    user = await sso_service.resolve_or_create_user(db, claims)

    # Reuse the normal login response's own token-issuing path (app/api/auth.py) rather than a
    # second copy of it here.
    tokens = await _issue_token_pair(db, user.id)

    settings = get_settings()
    fragment = f"access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    return RedirectResponse(f"{settings.oidc_frontend_callback_url}#{fragment}")

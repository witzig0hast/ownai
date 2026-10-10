import logging
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import _issue_token_pair
from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, create_sso_state_token, decode_sso_state_token
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.errors import APIError, InvalidSsoState, SsoNotConfigured
from app.services import sso_service

router = APIRouter(prefix="/auth/sso", tags=["auth"])
logger = logging.getLogger(__name__)


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


@router.get("/link")
async def sso_link(user: User = Depends(get_current_user)) -> dict[str, str]:
    """Starts the "link an existing account" flow from the settings page - unlike /login, this
    can't itself 307-redirect the browser: it's called via fetch() so the Authorization header
    identifying *which* account to link reaches us at all, and that header wouldn't survive a
    redirect anyway. The frontend reads this JSON body and does the full-page navigation itself."""
    if not sso_service.is_configured():
        raise SsoNotConfigured()
    nonce = secrets.token_urlsafe(16)
    state = create_sso_state_token(nonce, link_user_id=user.id)
    url = await sso_service.authorization_url(state=state, nonce=nonce)
    return {"url": url}


@router.delete("/link", status_code=204)
async def sso_unlink(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    user.oidc_subject = None
    await db.commit()


@router.get("/callback")
async def sso_callback(code: str, state: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    """Any failure here is caught and turned into a redirect to the frontend with ?error=&message=
    instead of the raw {"error": {...}} JSON body FastAPI's normal exception handler would
    produce - at the end of a browser redirect chain, nobody reads that JSON, so the frontend's
    own sso-callback page (web/src/app/sso-callback/page.tsx) renders it as a proper screen
    instead. 5xx failures are still logged server-side (mirroring app/main.py's api_error_handler,
    which never runs for these since we intercept them before they'd reach it)."""
    settings = get_settings()
    # Set as soon as it's known, read in the except block below too - lets a failed link attempt
    # send the user back to /settings instead of /login without the frontend having to guess
    # from whether it happens to still hold a session (see sso-callback/page.tsx).
    is_link_flow = False
    try:
        if not sso_service.is_configured():
            raise SsoNotConfigured()

        try:
            state_claims = decode_sso_state_token(state)
        except TokenError as exc:
            raise InvalidSsoState() from exc

        is_link_flow = state_claims.get("link_user_id") is not None
        claims = await sso_service.exchange_code_for_claims(code, nonce=state_claims["nonce"])

        if is_link_flow:
            await sso_service.link_existing_user(db, state_claims["link_user_id"], claims)
            return RedirectResponse(f"{settings.oidc_frontend_callback_url}?linked=1")

        user = await sso_service.resolve_or_create_user(db, claims)
        # Reuse the normal login response's own token-issuing path (app/api/auth.py) rather than
        # a second copy of it here.
        tokens = await _issue_token_pair(db, user.id)
        fragment = f"access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
        return RedirectResponse(f"{settings.oidc_frontend_callback_url}#{fragment}")
    except APIError as exc:
        if exc.status_code >= 500:
            logger.warning("GET /auth/sso/callback -> %s %s: %s", exc.status_code, exc.code, exc.message)
        context = "&context=link" if is_link_flow else ""
        query = f"error={exc.code}&message={quote(exc.message)}{context}"
        return RedirectResponse(f"{settings.oidc_frontend_callback_url}?{query}")

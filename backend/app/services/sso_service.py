import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.config import get_settings
from app.db.models import User
from app.errors import RegistrationClosed, RegistrationDeclined, RegistrationPending, SsoError
from app.services import admin_service


def _client() -> httpx.AsyncClient:
    """Separate factory purely so tests can monkeypatch it - same pattern as the other external
    services (weather_service._client, home_assistant_service._client, ...).

    local_address="0.0.0.0" forces outbound connections over IPv4 only - the same fix already
    needed for SMTP (email_service._connect_ipv4) and IMAP (same file): this container can carry
    a non-routable IPv6 address on its interface, and without this, a connection to a host whose
    DNS has an AAAA record tries IPv6 first and hangs/fails - even though IPv4 would work fine.
    Binding the local socket to the IPv4 wildcard address rules out IPv6 the same way those two
    did by restricting getaddrinfo() to AF_INET."""
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    return httpx.AsyncClient(timeout=10.0, transport=transport)


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.oidc_issuer_url
        and settings.oidc_client_id
        and settings.oidc_client_secret
        and settings.oidc_redirect_uri
    )


# The discovery document (authorization/token/jwks endpoints) almost never changes for a given
# issuer - cached per process rather than re-fetched on every login. Module-level, not
# get_settings()-cached, because it needs an actual network round trip, unlike Settings itself.
_discovery_cache: dict[str, Any] | None = None


async def _discovery_document() -> dict[str, Any]:
    global _discovery_cache
    if _discovery_cache is not None:
        return _discovery_cache
    settings = get_settings()
    issuer = (settings.oidc_issuer_url or "").rstrip("/")
    async with _client() as client:
        try:
            response = await client.get(f"{issuer}/.well-known/openid-configuration")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SsoError(f"SSO-Provider nicht erreichbar: {exc}") from exc
    _discovery_cache = response.json()
    return _discovery_cache


async def authorization_url(*, state: str, nonce: str) -> str:
    settings = get_settings()
    discovery = await _discovery_document()
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": settings.oidc_scopes,
        "state": state,
        "nonce": nonce,
    }
    return f"{discovery['authorization_endpoint']}?{urlencode(params)}"


async def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.get(jwks_uri)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SsoError(f"Signaturschlüssel (JWKS) nicht abrufbar: {exc}") from exc
    return response.json()


def _verify_id_token(id_token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    """Finds the matching key in an already-fetched JWKS document (see _fetch_jwks - fetched
    through our own IPv4-forced client, not PyJWT's built-in PyJWKClient, which does its own
    separate, un-forced network fetch and would reintroduce exactly the IPv6-hang risk _client()
    above exists to avoid) and verifies the token's signature/audience/issuer against it."""
    settings = get_settings()
    kid = jwt.get_unverified_header(id_token).get("kid")
    keys = jwks.get("keys", [])
    matching_jwk = next((k for k in keys if k.get("kid") == kid), None)
    if matching_jwk is None and len(keys) == 1:
        # Some providers omit "kid" entirely when they only ever sign with one key.
        matching_jwk = keys[0]
    if matching_jwk is None:
        raise SsoError("Kein passender Signaturschlüssel beim SSO-Provider gefunden (kid-Mismatch).")

    signing_key = jwt.PyJWK(matching_jwk).key
    return jwt.decode(
        id_token,
        signing_key,
        algorithms=["RS256", "ES256"],
        audience=settings.oidc_client_id,
        issuer=(settings.oidc_issuer_url or "").rstrip("/"),
    )


async def exchange_code_for_claims(code: str, *, nonce: str) -> dict[str, Any]:
    settings = get_settings()
    discovery = await _discovery_document()

    async with _client() as client:
        try:
            response = await client.post(
                discovery["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.oidc_redirect_uri,
                    "client_id": settings.oidc_client_id,
                    "client_secret": settings.oidc_client_secret,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SsoError(f"Code-Austausch beim SSO-Provider fehlgeschlagen: {exc}") from exc

    id_token = response.json().get("id_token")
    if not id_token:
        raise SsoError("SSO-Provider hat kein id_token zurückgegeben (scope 'openid' fehlt?).")

    jwks = await _fetch_jwks(discovery["jwks_uri"])
    try:
        claims = _verify_id_token(id_token, jwks)
    except jwt.PyJWTError as exc:
        # Include the token's own (unverified-signature, just for display) "iss"/"aud" alongside
        # what we expect - a bare "Invalid issuer"/"Invalid audience" from PyJWT gives no hint
        # which value is wrong, and this is the single most common OIDC misconfiguration
        # (Authentik, for instance, issues "https://host/application/o/<slug>/", not just the
        # bare host some people put in OIDC_ISSUER_URL).
        unverified = jwt.decode(id_token, options={"verify_signature": False})
        raise SsoError(
            f"id_token ungültig: {exc} "
            f"(erhalten: iss={unverified.get('iss')!r} aud={unverified.get('aud')!r}; "
            f"erwartet: iss={(settings.oidc_issuer_url or '').rstrip('/')!r} aud={settings.oidc_client_id!r})"
        ) from exc

    # Checked ourselves on top of signature/audience/issuer (already enforced by jwt.decode
    # above) - the nonce ties this specific id_token back to the authorization request *we*
    # started, so a stolen/replayed id_token from a different login attempt is rejected even if
    # its signature is otherwise perfectly valid.
    if claims.get("nonce") != nonce:
        raise SsoError("nonce im id_token stimmt nicht überein (möglicher Replay-Versuch).")
    if not claims.get("email"):
        raise SsoError("SSO-Provider hat keine E-Mail-Adresse geliefert (scope 'email' fehlt?).")

    return claims


def _check_approval(user: User) -> User:
    # Same gate as the password login path (app/api/auth.py) - an SSO identity gets no special
    # treatment around the approval-before-login policy (see DECISIONS.md #13).
    if user.approval_status == "pending":
        raise RegistrationPending()
    if user.approval_status == "declined":
        raise RegistrationDeclined()
    return user


async def resolve_or_create_user(db: AsyncSession, claims: dict[str, Any]) -> User:
    """Maps verified OIDC claims to an OwnAI account: an existing link (oidc_subject) wins: then
    an existing password-based account with the same email gets linked (no duplicate account for
    one person); otherwise a brand-new account is bootstrapped - deliberately mirroring
    POST /auth/register's own first-user-is-admin/approval-gate logic (app/api/auth.py) rather
    than sharing a helper with it, since the two differ in what happens on an email collision
    (register rejects it, SSO links to it)."""
    subject = claims["sub"]
    email = claims["email"]
    display_name = claims.get("name") or claims.get("preferred_username") or email.split("@")[0]

    result = await db.execute(select(User).where(User.oidc_subject == subject))
    user = result.scalar_one_or_none()
    if user is not None:
        return _check_approval(user)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        user.oidc_subject = subject
        await db.commit()
        await db.refresh(user)
        return _check_approval(user)

    is_first_user = await admin_service.user_count(db) == 0
    if not is_first_user:
        app_settings = await admin_service.get_settings(db)
        if not app_settings.registration_open:
            raise RegistrationClosed()

    user = User(
        email=email,
        # Random and never shared with anyone - an SSO-only account simply can never match this
        # via POST /auth/login, so every other password-login code path stays a plain,
        # non-nullable password_hash check with no "| None" branches to carry.
        password_hash=hash_password(secrets.token_urlsafe(32)),
        display_name=display_name,
        oidc_subject=subject,
        is_admin=is_first_user,
        approval_status="approved" if is_first_user else "pending",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _check_approval(user)

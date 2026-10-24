from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./ownai.db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "dev-only-insecure-secret-change-me"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "hermes3:8b"
    ollama_embed_model: str = "nomic-embed-text"
    # Optional separate (smaller/faster) model for conversation auto-titling; falls back to
    # ollama_chat_model when unset - see ollama_client.generate_title.
    ollama_title_model: str | None = None
    # How long Ollama keeps the model loaded in (V)RAM after the last request. Applied to every
    # chat call, not just the warmup one (see app/api/chat.py's /chat/warmup), so normal usage
    # already keeps it warm between messages. Default "-1" (never unload) assumes a GPU dedicated
    # to OwnAI, as recommended in .env.example - override to e.g. "30m" if the GPU is shared.
    ollama_keep_alive: str = "-1"
    # Optional vision-capable model (e.g. "llama3.2-vision", "llava") for image understanding
    # (see app/services/vision_service.py) - unset by default since it's a separate model the
    # user has to pull themselves; OCR (pytesseract) works regardless of this.
    ollama_vision_model: str | None = None

    # Wyoming-protocol ASR (speech-to-text), e.g. an existing wyoming-whisper instance.
    whisper_host: str = "host.docker.internal"
    whisper_port: int = 10300
    whisper_language: str = "de"

    # Self-hosted, OpenAI-compatible TTS server (e.g. Godelaune/Kokoro-82M-ONNX-German-Martin,
    # run separately - see infra/kokoro/README.md) for reading replies aloud with a natural
    # neural voice instead of the browser's built-in speechSynthesis. Unset means server-side
    # TTS is disabled and the web app falls back to browser TTS entirely (see tts_service.py).
    kokoro_tts_base_url: str | None = None
    kokoro_tts_voice: str = "martin"

    # Where the create_file tool's output lives on disk, per user/conversation (see
    # app/services/file_service.py) - mount a volume here in production so files survive
    # container restarts.
    files_storage_dir: str = "./data/files"
    files_max_content_chars: int = 20000

    # System-wide default SMTP account the assistant sends email from when a user hasn't
    # connected their own (see app/services/email_service.py). All optional - if unset, only
    # users with their own connected account can use the send_email tool.
    system_smtp_host: str | None = None
    system_smtp_port: int = 587
    system_smtp_username: str | None = None
    system_smtp_password: str | None = None
    system_smtp_from_address: str | None = None
    system_smtp_use_tls: bool = True

    # Web Push (VAPID). Generate a key pair once with `vapid --gen` (py-vapid, already a
    # dependency) and paste the resulting private/public keys here - both are required for
    # push to work at all; unset means push is silently unavailable (see push_service.py).
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    # Contact address the push service can reach you at if it flags your usage - required by
    # the Web Push protocol, has to be a "mailto:" or "https:" URI.
    vapid_subject: str = "mailto:admin@example.com"

    # Optional SSO login via any OIDC-compliant identity provider (e.g. a self-hosted Authentik
    # instance) - added alongside the existing email/password login, never replacing it. All
    # four below unset (the default) means SSO is simply off: GET /auth/sso/login then responds
    # with 404 sso_not_configured and the frontend doesn't show the button at all.
    oidc_issuer_url: str | None = None  # e.g. "https://auth.example.com/application/o/ownai/"
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    # Must exactly match a "Redirect URI" configured on the provider side. Points at this
    # backend's own callback endpoint (GET /auth/sso/callback), not the frontend.
    oidc_redirect_uri: str | None = None
    oidc_scopes: str = "openid email profile"
    # Where the browser ends up once the backend has finished the token exchange - the
    # frontend's own callback page, which reads the issued OwnAI tokens from the URL fragment
    # and stores them exactly like a normal password login (see
    # web/src/app/sso-callback/page.tsx). Fragment, not query string, so the tokens never hit
    # this backend's or any proxy's access logs on that final redirect.
    oidc_frontend_callback_url: str = "http://localhost:3000/sso-callback"

    cors_origins: str = "http://localhost:3000"

    # IANA time zone that "heute", reminder times ("jeden Montag um 8"), the birthday push and the
    # time given to the LLM refer to. The container's own clock is UTC, so without this a
    # reminder set for 8:30 fired at 8:30 UTC (10:30 in Germany in summer).
    timezone: str = "Europe/Berlin"

    # Brute-force protection for POST /auth/login (see app/auth/rate_limit.py). Failed attempts
    # are counted per (email, client IP) within a sliding window, plus a looser per-email cap
    # across all IPs so a distributed guess run is throttled too.
    login_max_failures: int = 5
    login_max_failures_per_email: int = 20
    login_failure_window_minutes: int = 15
    # Header carrying the real client IP when running behind a reverse proxy / Cloudflare (e.g.
    # "CF-Connecting-IP" or "X-Forwarded-For"). Unset means the TCP peer address is used - which
    # behind Docker's bridge is the same gateway IP for everyone, so the per-IP limit then
    # effectively becomes per-email. Only set this if that header is actually set by your proxy;
    # a client could otherwise send it itself.
    trusted_client_ip_header: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

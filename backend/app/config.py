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
    # already keeps it warm between messages.
    ollama_keep_alive: str = "30m"
    # Optional vision-capable model (e.g. "llama3.2-vision", "llava") for image understanding
    # (see app/services/vision_service.py) - unset by default since it's a separate model the
    # user has to pull themselves; OCR (pytesseract) works regardless of this.
    ollama_vision_model: str | None = None

    # Wyoming-protocol ASR (speech-to-text), e.g. an existing wyoming-whisper instance.
    whisper_host: str = "host.docker.internal"
    whisper_port: int = 10300
    whisper_language: str = "de"

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

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

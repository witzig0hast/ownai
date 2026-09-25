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

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

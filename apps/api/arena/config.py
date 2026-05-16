"""Application settings, sourced from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_log_level: str = "info"
    api_allowed_origins: str = "http://localhost:3000"

    # Data
    database_url: str = "sqlite+aiosqlite:///./arena.db"
    redis_url: str = "memory://"

    # Sim
    sim_tick_seconds: float = 1.0
    sim_autoseed: bool = True
    sim_history_window_s: int = 3600

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.api_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

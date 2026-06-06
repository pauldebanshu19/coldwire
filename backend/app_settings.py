"""Infra settings for the API + workers (separate from the pure engine's
core.config, which stays web/DB-free).

Zero-infra local default: SQLite + in-process dispatch + in-memory event bus.
Set DATABASE_URL + REDIS_URL to switch to Postgres + Celery/Redis.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # async driver URLs. Local default needs no server running.
    database_url: str = "sqlite+aiosqlite:///./conduit.db"
    redis_url: str = ""  # empty -> Celery eager / in-process dispatch + memory bus

    jwt_secret: str = "dev-insecure-change-me"
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: str = ""           # comma-separated exact origins (prod)
    dev_mode: bool = True            # set false in production
    auto_create_tables: bool = True  # create_all on startup (dev / sqlite)

    # per-user guardrails (scaling / fairness)
    max_jobs_per_user_per_day: int = 1000

    @property
    def use_celery(self) -> bool:
        """Real queue when Redis is configured; otherwise in-process tasks."""
        return bool(self.redis_url)

    @property
    def broker_url(self) -> str:
        return self.redis_url or "memory://"

    @property
    def result_backend(self) -> str:
        return self.redis_url or "cache+memory://"


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()

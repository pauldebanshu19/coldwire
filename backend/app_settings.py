"""Infra settings for the API + workers (separate from the pure engine's
core.config, which stays web/DB-free).

Zero-infra local default: SQLite + in-process dispatch + in-memory event bus.
Set DATABASE_URL + REDIS_URL to switch to Postgres + Celery/Redis.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Pin the default sqlite file to the backend dir so the DB is the same
# regardless of the working directory uvicorn is launched from.
_DEFAULT_SQLITE = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent / 'conduit.db'}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # async driver URLs. Local default needs no server running.
    database_url: str = _DEFAULT_SQLITE

    @field_validator("database_url")
    @classmethod
    def _to_async_driver(cls, v: str) -> str:
        """Accept a raw Postgres/Supabase URI and coerce it to the async driver.
        `postgresql://u:p@host/db?sslmode=require` -> `postgresql+asyncpg://u:p@host/db`
        (TLS + pooler options are handled in db/session connect_args)."""
        v = v.strip().split("?")[0]
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix):]
        return v
    redis_url: str = ""  # empty -> Celery eager / in-process dispatch + memory bus

    # ── Supabase Auth ──
    # Tokens are verified against {supabase_url}/auth/v1/user using the
    # publishable key. No secret is stored server-side.
    supabase_url: str = ""
    supabase_publishable_key: str = ""

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

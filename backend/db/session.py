"""Async engine + session factory. One async stack everywhere (API and the
Celery tasks, which wrap async work in `asyncio.run`)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.pool import NullPool

from app_settings import get_app_settings
from .base import Base

_settings = get_app_settings()


def _connect_args_for(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if "+asyncpg" in url:
        # statement_cache_size=0 is required behind a transaction pooler
        # (Supabase Supavisor / PgBouncer). Supabase requires TLS.
        args: dict = {"statement_cache_size": 0}
        if "supabase.co" in url or "supabase.com" in url or "pooler.supabase" in url:
            args["ssl"] = "require"
        return args
    return {}


_connect_args = _connect_args_for(_settings.database_url)

# NullPool: don't reuse connections across event loops. Celery runs each task in
# its own asyncio.run loop, and a pooled asyncpg connection bound to a prior
# (closed) loop raises "attached to a different loop". A fresh connection per
# session avoids that; real pooling is delegated to PgBouncer in production.
engine = create_async_engine(
    _settings.database_url, future=True, connect_args=_connect_args, poolclass=NullPool,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models() -> None:
    """Dev/sqlite bootstrap. Production uses Alembic migrations."""
    # ensure models are imported so metadata is populated
    from . import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

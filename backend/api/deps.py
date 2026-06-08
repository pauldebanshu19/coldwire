"""FastAPI dependencies — DB session + current user from a Supabase token.

The Supabase user (id + email) is upserted into the local users table so jobs
stay relationally scoped; auth itself lives entirely in Supabase.
"""

from __future__ import annotations

from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app_settings import get_app_settings
from db.models import User
from db.session import AsyncSessionLocal, init_models
from .supabase_auth import verify_token

_tables_ready = False


async def ensure_tables(force: bool = False) -> None:
    """Create tables on first DB use (idempotent). Belt-and-suspenders so a
    request never 500s with 'no such table' if startup was bypassed or the
    sqlite file was emptied under a running server."""
    global _tables_ready
    if _tables_ready and not force:
        return
    if get_app_settings().auto_create_tables:
        await init_models()
    _tables_ready = True


async def get_session() -> AsyncIterator[AsyncSession]:
    await ensure_tables()
    async with AsyncSessionLocal() as session:
        yield session


async def _fetch_or_create_user(session: AsyncSession, info: dict) -> User:
    user = await session.get(User, info["id"])
    if user is None:
        user = User(id=info["id"], email=info["email"], password_hash="")
        session.add(user)
        await session.commit()
    elif info["email"] and user.email != info["email"]:
        user.email = info["email"]
        await session.commit()
    return user


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    info = await verify_token(token)
    if not info:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    try:
        return await _fetch_or_create_user(session, info)
    except (OperationalError, ProgrammingError):
        # Tables missing (e.g. the sqlite file was emptied under us). Recreate
        # and retry once — never surface a 500 for a recoverable schema gap.
        await session.rollback()
        await ensure_tables(force=True)
        return await _fetch_or_create_user(session, info)

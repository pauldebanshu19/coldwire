"""Supabase token verification.

Validates a Supabase access token by introspecting it against
`{SUPABASE_URL}/auth/v1/user` with the publishable key — no JWT secret needs to
live on the server, and it works regardless of the token's signing algorithm.
Validated tokens are cached briefly to avoid a network hop per request.
"""

from __future__ import annotations

import time
from typing import Optional, TypedDict

import httpx

from app_settings import get_app_settings

_CACHE_TTL = 300  # seconds
_cache: dict[str, tuple[float, "SupabaseUser"]] = {}


class SupabaseUser(TypedDict):
    id: str
    email: str


async def verify_token(token: str) -> Optional[SupabaseUser]:
    if not token:
        return None
    settings = get_app_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        return None

    now = time.time()
    cached = _cache.get(token)
    if cached and cached[0] > now:
        return cached[1]

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_publishable_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None

    data = resp.json()
    uid = data.get("id")
    if not uid:
        return None
    user: SupabaseUser = {"id": str(uid), "email": data.get("email") or ""}
    _cache[token] = (now + _CACHE_TTL, user)
    return user

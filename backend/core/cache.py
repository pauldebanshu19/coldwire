"""Result cache for paid provider calls (cost control + speed).

Keyed on provider + input, e.g. `ocean:lookalikes:acme.com`. Phase 1 ships an
on-disk JSON cache; the async interface matches a future Redis cache so two
users seeding the same domain spend credits once.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional


class Cache:
    async def get(self, key: str) -> Optional[Any]:  # pragma: no cover - interface
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int) -> None:  # pragma: no cover
        raise NotImplementedError


class NullCache(Cache):
    async def get(self, key: str) -> Optional[Any]:
        return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        return None


class FileCache(Cache):
    """Simple TTL'd JSON file cache. Good enough for the CLI / demo."""

    def __init__(self, directory: str) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.dir / f"{digest}.json"

    async def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if payload.get("expires_at", 0) < time.time():
            path.unlink(missing_ok=True)
            return None
        return payload.get("value")

    async def set(self, key: str, value: Any, ttl: int) -> None:
        path = self._path(key)
        payload = {"key": key, "value": value, "expires_at": time.time() + ttl}
        try:
            path.write_text(json.dumps(payload))
        except (OSError, TypeError):
            pass


class RedisCache(Cache):
    """Shared result cache across all workers (paid-call dedup is global)."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis
        self._r = aioredis.from_url(url, decode_responses=True)

    @staticmethod
    def _k(key: str) -> str:
        return f"coldwire:cache:{key}"

    async def get(self, key: str) -> Optional[Any]:
        try:
            raw = await self._r.get(self._k(key))
        except Exception:  # noqa: BLE001 - cache must never break the run
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            await self._r.set(self._k(key), json.dumps(value), ex=max(ttl, 1))
        except (TypeError, Exception):  # noqa: BLE001
            return None


def build_cache(enabled: bool, directory: str, redis_url: str = "") -> Cache:
    if redis_url:
        return RedisCache(redis_url)
    return FileCache(directory) if enabled else NullCache()

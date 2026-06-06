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


def build_cache(enabled: bool, directory: str) -> Cache:
    return FileCache(directory) if enabled else NullCache()

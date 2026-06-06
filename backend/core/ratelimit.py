"""Token-bucket rate limiter.

Phase 1 uses an in-process async bucket per provider. The interface
(`acquire`) is identical to what a Redis-backed global bucket will expose in
Phase 4, so workers can swap implementations without touching call sites.
"""

from __future__ import annotations

import asyncio
import time


class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: float | None = None) -> None:
        self.rate = max(rate_per_sec, 0.001)
        self.capacity = capacity if capacity is not None else max(rate_per_sec, 1.0)
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Block until `tokens` are available, then consume them."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
                self._updated = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait = deficit / self.rate
            await asyncio.sleep(wait)


class RateLimiterRegistry:
    """One bucket per provider, shared across all clients in a process."""

    def __init__(self, rps: dict[str, float]) -> None:
        self._buckets = {name: TokenBucket(rate) for name, rate in rps.items()}

    async def acquire(self, provider: str, tokens: float = 1.0) -> None:
        bucket = self._buckets.get(provider)
        if bucket is not None:
            await bucket.acquire(tokens)

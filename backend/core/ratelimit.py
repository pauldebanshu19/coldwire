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


# Atomic token-bucket in Redis → the limit is GLOBAL across every worker
# process, not per-process. Returns {allowed(0|1), wait_seconds}.
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])
local cap = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local d = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(d[1]); local ts = tonumber(d[2])
if tokens == nil then tokens = cap; ts = now end
tokens = math.min(cap, tokens + math.max(0, now - ts) * rate)
local allowed = 0; local wait = 0
if tokens >= requested then
  allowed = 1; tokens = tokens - requested
else
  wait = (requested - tokens) / rate
end
redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('PEXPIRE', key, math.ceil((cap / rate) * 1000) + 2000)
return {allowed, tostring(wait)}
"""


class RedisRateLimiterRegistry:
    """Global per-provider token bucket backed by Redis (shared across workers)."""

    def __init__(self, url: str, rps: dict[str, float]) -> None:
        import redis.asyncio as aioredis
        self._r = aioredis.from_url(url, decode_responses=True)
        self._rps = rps

    async def acquire(self, provider: str, tokens: float = 1.0) -> None:
        rate = self._rps.get(provider)
        if not rate:
            return
        cap = max(rate, 1.0)
        key = f"coldwire:rl:{provider}"
        while True:
            try:
                res = await self._r.eval(_TOKEN_BUCKET_LUA, 1, key, rate, cap, time.time(), tokens)
                allowed, wait = int(res[0]), float(res[1])
            except Exception:  # noqa: BLE001 - never let the limiter break the run
                return
            if allowed:
                return
            await asyncio.sleep(min(wait, 5.0))

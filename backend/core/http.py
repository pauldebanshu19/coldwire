"""Shared async HTTP transport.

Every external call goes through `ProviderHTTP.request_json`, which:
  1. checks the result cache (paid-call dedup),
  2. acquires a rate-limit token (global per provider),
  3. retries 429/5xx/timeouts with exponential backoff + jitter,
  4. honours `Retry-After`,
  5. fails fast on 401/400/403 (never retry an auth failure into a ban).
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Optional

import httpx

from .cache import Cache
from .errors import AuthError, RetryableError, TerminalError
from .logging import get_logger
from .ratelimit import RateLimiterRegistry

log = get_logger("http")

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def _parse_retry_after(value: str | None) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None  # HTTP-date form ignored; backoff covers it


class ProviderHTTP:
    def __init__(
        self,
        client: httpx.AsyncClient,
        limiter: RateLimiterRegistry,
        cache: Cache,
        *,
        max_retries: int = 4,
        base_backoff: float = 0.5,
        max_backoff: float = 30.0,
    ) -> None:
        self._client = client
        self._limiter = limiter
        self._cache = cache
        self._max_retries = max_retries
        self._base_backoff = base_backoff
        self._max_backoff = max_backoff

    async def request_json(
        self,
        provider: str,
        method: str,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        cache_ttl: int = 0,
    ) -> Any:
        if cache_key:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                log.debug("cache hit %s", cache_key)
                return cached

        result = await self._send_with_retry(provider, method, url, headers, json, params)

        if cache_key and cache_ttl > 0 and result is not None:
            await self._cache.set(cache_key, result, cache_ttl)
        return result

    async def _send_with_retry(self, provider, method, url, headers, json, params) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            await self._limiter.acquire(provider)
            try:
                resp = await self._client.request(
                    method, url, headers=headers, json=json, params=params
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = RetryableError(f"{provider} network error: {exc}", provider=provider)
                await self._sleep_before_retry(attempt, None, str(last_exc))
                continue

            if resp.status_code < 300:
                if not resp.content:
                    return {}
                try:
                    return resp.json()
                except ValueError:
                    return {"_raw": resp.text}

            exc = self._classify(provider, resp)
            if isinstance(exc, RetryableError):
                last_exc = exc
                await self._sleep_before_retry(attempt, exc.retry_after, str(exc))
                continue
            raise exc  # terminal — stop now

        assert last_exc is not None
        log.error("%s exhausted %d retries: %s", provider, self._max_retries, last_exc)
        raise last_exc

    def _classify(self, provider: str, resp: httpx.Response) -> Exception:
        status = resp.status_code
        snippet = resp.text[:300]
        if status in (401, 403):
            return AuthError(f"{provider} auth failed ({status}): {snippet}",
                             provider=provider, status=status)
        if status in RETRYABLE_STATUS:
            return RetryableError(
                f"{provider} retryable {status}: {snippet}",
                provider=provider, status=status,
                retry_after=_parse_retry_after(resp.headers.get("Retry-After")),
            )
        return TerminalError(f"{provider} error {status}: {snippet}",
                             provider=provider, status=status)

    async def _sleep_before_retry(self, attempt: int, retry_after: Optional[float], why: str) -> None:
        if attempt >= self._max_retries:
            return  # caller will raise
        if retry_after is not None:
            delay = min(retry_after, self._max_backoff)
        else:
            delay = min(self._base_backoff * (2 ** (attempt - 1)), self._max_backoff)
            delay += random.uniform(0, delay * 0.25)  # jitter
        log.warning("retry %d after %.1fs — %s", attempt, delay, why)
        await asyncio.sleep(delay)

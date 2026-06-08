import asyncio

import httpx
import pytest

from core.breaker import BreakerRegistry, CircuitBreaker, CircuitOpenError
from core.cache import NullCache
from core.errors import RetryableError
from core.http import ProviderHTTP
from core.ratelimit import RateLimiterRegistry


async def test_breaker_opens_then_half_opens_and_recovers():
    b = CircuitBreaker("x", fail_max=3, reset_timeout=0.05)
    for _ in range(3):
        await b.record_failure()
    with pytest.raises(CircuitOpenError):
        await b.check()                 # open → fast-fail
    await asyncio.sleep(0.06)
    await b.check()                     # cooldown passed → half-open, trial allowed
    await b.record_success()
    await b.check()                     # closed again


async def test_http_opens_breaker_after_repeated_failures():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, json={"e": 1})   # always retryable-fail

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    http = ProviderHTTP(
        client, RateLimiterRegistry({"p": 1000}), NullCache(),
        breakers=BreakerRegistry(fail_max=2, reset_timeout=30),
        max_retries=1, base_backoff=0.001,
    )

    # two failing calls trip the breaker (each exhausts retries = 1 failure)
    for _ in range(2):
        with pytest.raises(RetryableError):
            await http.request_json("p", "GET", "https://x/y")

    before = calls["n"]
    # next call is short-circuited — no transport hit
    with pytest.raises(CircuitOpenError):
        await http.request_json("p", "GET", "https://x/y")
    assert calls["n"] == before

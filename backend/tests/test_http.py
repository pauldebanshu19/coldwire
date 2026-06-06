import httpx
import pytest

from core.cache import NullCache
from core.errors import AuthError, RetryableError
from core.http import ProviderHTTP
from core.ratelimit import RateLimiterRegistry


def make_http(handler, max_retries=3):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    limiter = RateLimiterRegistry({"test": 1000})
    return ProviderHTTP(client, limiter, NullCache(), max_retries=max_retries, base_backoff=0.001)


async def test_retries_429_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"e": 1})
        return httpx.Response(200, json={"ok": True})

    http = make_http(handler)
    result = await http.request_json("test", "POST", "https://x/y", json={})
    assert result == {"ok": True}
    assert calls["n"] == 3


async def test_auth_error_is_terminal_no_retry():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    http = make_http(handler)
    with pytest.raises(AuthError):
        await http.request_json("test", "POST", "https://x/y", json={})
    assert calls["n"] == 1  # never retried


async def test_exhausts_retries_then_raises():
    def handler(request):
        return httpx.Response(503, json={"e": 1})

    http = make_http(handler, max_retries=2)
    with pytest.raises(RetryableError):
        await http.request_json("test", "GET", "https://x/y")

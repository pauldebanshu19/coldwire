"""Client factory: wires HTTP transport + rate limiter + cache, picks real
vs mock providers. Email resolution (Stage 3) runs on Prospeo `enrich-person`.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

import httpx

from ..breaker import BreakerRegistry
from ..cache import build_cache
from ..config import Settings
from ..http import ProviderHTTP
from ..logging import get_logger
from ..models import Company, Contact, Email
from ..ratelimit import RateLimiterRegistry, RedisRateLimiterRegistry
from .brevo import BrevoClient
from .mock import MockBrevoClient, MockOceanClient, MockProspeoClient, MockResolver
from .ocean import OceanClient
from .prospeo import ProspeoClient

log = get_logger("clients")


class Resolver(Protocol):
    async def resolve_email(self, linkedin_url: str) -> Email | None: ...
    name: str


@dataclass
class Clients:
    ocean: object        # find_lookalikes(seed) -> list[Company]
    prospeo: object      # find_contacts(domain) -> list[Contact]
    resolver: object     # resolve_email(linkedin_url) -> Email | None
    brevo: object        # send(...) -> message_id
    resolver_name: str


@contextlib.asynccontextmanager
async def build_clients(settings: Settings) -> AsyncIterator[Clients]:
    if settings.mock:
        log.info("MOCK mode — no real provider calls, zero credits spent")
        yield Clients(
            ocean=MockOceanClient(settings),
            prospeo=MockProspeoClient(settings),
            resolver=MockResolver(settings),
            brevo=MockBrevoClient(settings),
            resolver_name="mock",
        )
        return

    rps = {p: settings.provider_rps(p) for p in ("ocean", "prospeo", "brevo")}
    if settings.redis_url:
        log.info("Using Redis-global rate limiter + cache")
        limiter: object = RedisRateLimiterRegistry(settings.redis_url, rps)
    else:
        limiter = RateLimiterRegistry(rps)
    cache = build_cache(settings.cache_enabled, settings.cache_dir, settings.redis_url)
    breakers = BreakerRegistry()

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        http = ProviderHTTP(client, limiter, cache, breakers=breakers,
                            max_retries=settings.max_retries)

        ocean = OceanClient(http, settings)
        prospeo = ProspeoClient(http, settings)
        brevo = BrevoClient(http, settings)

        # Stage 3 resolves emails via Prospeo enrich-person (same client).
        yield Clients(
            ocean=ocean, prospeo=prospeo, resolver=prospeo, brevo=brevo,
            resolver_name="prospeo-enrich",
        )

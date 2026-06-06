"""Client factory: wires HTTP transport + rate limiter + cache, picks real
vs mock providers, and routes email resolution to Eazyreach or (when no
Eazyreach key is set) the Prospeo enrich-person fallback.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

import httpx

from ..cache import build_cache
from ..config import Settings
from ..http import ProviderHTTP
from ..logging import get_logger
from ..models import Company, Contact, Email
from ..ratelimit import RateLimiterRegistry
from .brevo import BrevoClient
from .eazyreach import EazyreachClient
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

    limiter = RateLimiterRegistry(
        {p: settings.provider_rps(p) for p in ("ocean", "prospeo", "eazyreach", "brevo")}
    )
    cache = build_cache(settings.cache_enabled, settings.cache_dir)

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        http = ProviderHTTP(client, limiter, cache, max_retries=settings.max_retries)

        ocean = OceanClient(http, settings)
        prospeo = ProspeoClient(http, settings)
        brevo = BrevoClient(http, settings)

        if settings.eazyreach_api_key:
            resolver: object = EazyreachClient(http, settings)
            resolver_name = "eazyreach"
        else:
            log.warning("No EAZYREACH_API_KEY — resolving emails via Prospeo enrich-person")
            resolver = prospeo  # ProspeoClient also implements resolve_email
            resolver_name = "prospeo-enrich"

        yield Clients(
            ocean=ocean, prospeo=prospeo, resolver=resolver, brevo=brevo,
            resolver_name=resolver_name,
        )

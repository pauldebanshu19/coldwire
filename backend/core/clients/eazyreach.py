"""Stage 3 provider — Eazyreach (LinkedIn URL -> verified work email).

Eazyreach's API docs sit behind the dashboard login, so the exact endpoint /
auth header is confirmed once the key + docs arrive. The auth header and path
are isolated here and the response parser is defensive, so wiring the real
shape is a one-spot change. Until a key is set, the factory routes Stage 3 to
the Prospeo enrich-person fallback instead (see clients/__init__.py).
"""

from __future__ import annotations

from ..config import Settings
from ..http import ProviderHTTP
from ..logging import get_logger
from ..models import Email
from ._util import first
from .prospeo import _map_status

log = get_logger("eazyreach")


class EazyreachClient:
    provider = "eazyreach"
    name = "eazyreach"

    def __init__(self, http: ProviderHTTP, settings: Settings) -> None:
        self._http = http
        self._s = settings
        # TODO(confirm): exact path from Eazyreach API docs once available.
        self._url = f"{settings.eazyreach_base_url.rstrip('/')}/v1/email-finder"

    def _headers(self) -> dict[str, str]:
        # TODO(confirm): Eazyreach may use `Authorization: Bearer` instead.
        return {"x-api-key": self._s.eazyreach_api_key, "Content-Type": "application/json"}

    async def resolve_email(self, linkedin_url: str) -> Email | None:
        if not linkedin_url:
            return None
        body = {"linkedin_url": linkedin_url, "profile_url": linkedin_url}
        payload = await self._http.request_json(
            self.provider, "POST", self._url,
            headers=self._headers(), json=body,
            cache_key=f"eazyreach:{linkedin_url.strip().lower()}",
            cache_ttl=self._s.cache_ttl_seconds,
        )
        node = payload if isinstance(payload, dict) else {}
        node = node.get("data", node) if isinstance(node.get("data"), dict) else node
        addr = first(node, ("email", "work_email", "email_address", "personal_email"))
        if not addr or "@" not in str(addr):
            return None
        status = str(first(node, ("status", "email_status", "verification_status"), "UNKNOWN"))
        return Email(
            address=str(addr),
            status=_map_status(status),
            verification_method=first(node, ("verification_method", "source")),
            raw=node,
        )

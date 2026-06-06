"""Stage 1 provider — Ocean.io lookalike company search.

  POST {base}/v3/search/companies
  Auth:   header `x-api-token`
  Body:   {"size": N, "searchAfter": cursor|null,
           "companiesFilters": {"lookalikeDomains": [seed]}}
  Resp:   {"searchAfter": cursor, "total": int, "creditsUsed": float,
           "companies": [{"company": {"domain", "companySize",
                                      "industries", "primaryCountry", ...}}]}

Pagination is cursor-based via `searchAfter`. Each call spends Ocean credits, so
`size` is capped at the requested company count and results are cached.
Schema confirmed against the live v3 OpenAPI spec.
"""

from __future__ import annotations

from ..config import Settings
from ..http import ProviderHTTP
from ..logging import get_logger
from ..models import Company, normalize_domain
from ._util import as_list, first

log = get_logger("ocean")


class OceanClient:
    provider = "ocean"

    def __init__(self, http: ProviderHTTP, settings: Settings) -> None:
        self._http = http
        self._s = settings
        self._url = f"{settings.ocean_base_url.rstrip('/')}/v3/search/companies"

    def _headers(self) -> dict[str, str]:
        return {"x-api-token": self._s.ocean_api_key, "Content-Type": "application/json"}

    async def find_lookalikes(self, seed_domain: str) -> list[Company]:
        seed = normalize_domain(seed_domain)
        limit = self._s.max_companies
        out: list[Company] = []
        seen: set[str] = {seed}
        cursor: str | None = None
        credits = 0.0

        while len(out) < limit:
            body: dict = {
                "size": min(limit - len(out), 50),
                "companiesFilters": {"lookalikeDomains": [seed]},
            }
            if cursor:
                body["searchAfter"] = cursor

            payload = await self._http.request_json(
                self.provider, "POST", self._url,
                headers=self._headers(), json=body,
                cache_key=f"ocean:lookalikes:{seed}:{cursor or 'p0'}:{body['size']}",
                cache_ttl=self._s.cache_ttl_seconds,
            )
            credits += float(payload.get("creditsUsed", 0) or 0) if isinstance(payload, dict) else 0
            rows = as_list(payload, ("companies",))
            if not rows:
                break

            for row in rows:
                # each row is {"company": {...}} — unwrap, but tolerate flat too
                comp = row.get("company") if isinstance(row.get("company"), dict) else row
                domain_raw = first(comp, ("domain", "website", "primaryDomain"))
                if not domain_raw:
                    continue
                domain = normalize_domain(str(domain_raw))
                if not domain or "." not in domain or domain in seen:
                    continue
                seen.add(domain)
                industries = first(comp, ("industries", "industryCategories"))
                try:
                    out.append(Company(
                        domain=domain,
                        name=first(comp, ("name", "companyName", "legalName")),
                        size=first(comp, ("companySize", "employeeCountOcean", "size")),
                        industry=industries[0] if isinstance(industries, list) and industries
                                 else (industries if isinstance(industries, str) else None),
                        country=first(comp, ("primaryCountry", "country")),
                        raw=comp,
                    ))
                except ValueError:
                    continue
                if len(out) >= limit:
                    break

            cursor = payload.get("searchAfter") if isinstance(payload, dict) else None
            if not cursor or len(rows) == 0:
                break

        log.info("Ocean: %d lookalike companies for %s (%.0f credits)", len(out), seed, credits)
        return out

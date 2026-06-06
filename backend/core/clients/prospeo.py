"""Stage 2 provider — Prospeo decision-maker search (+ enrich fallback).

  Search:  POST {base}/search-person     (domain -> C-suite/VP + LinkedIn)
  Enrich:  POST {base}/enrich-person      (LinkedIn URL -> verified email)
  Auth:    header `X-KEY`

`enrich_resolve` doubles as the Stage-3 resolver when no Eazyreach key is set,
so the pipeline runs end-to-end on the Prospeo key alone.
"""

from __future__ import annotations

from ..config import Settings
from ..http import ProviderHTTP
from ..logging import get_logger
from ..models import Contact, Email, EmailStatus, normalize_domain
from ._util import as_list, first

log = get_logger("prospeo")

# C-suite / VP-level only — per the brief. Exact enum values from
# /api-docs/enum/seniorities (filter key is `person_seniority`).
SENIORITY_FILTER = ["Founder/Owner", "C-Suite", "Partner", "Vice President", "Head"]
PAGE_SIZE = 25


class ProspeoClient:
    provider = "prospeo"
    name = "prospeo-enrich"  # when used as resolver

    def __init__(self, http: ProviderHTTP, settings: Settings) -> None:
        self._http = http
        self._s = settings
        base = settings.prospeo_base_url.rstrip("/")
        self._search_url = f"{base}/search-person"
        self._enrich_url = f"{base}/enrich-person"

    def _headers(self) -> dict[str, str]:
        return {"X-KEY": self._s.prospeo_api_key, "Content-Type": "application/json"}

    # ── Stage 2 ──────────────────────────────────────────────────────
    async def find_contacts(self, domain: str) -> list[Contact]:
        domain = normalize_domain(domain)
        limit = self._s.max_contacts_per_company
        out: list[Contact] = []
        seen_li: set[str] = set()
        page = 1

        total_pages = 1
        while len(out) < limit and page <= total_pages:
            body = {
                "page": page,
                "filters": {
                    "company": {"websites": {"include": [domain]}},
                    "person_seniority": {"include": SENIORITY_FILTER},
                },
            }
            payload = await self._http.request_json(
                self.provider, "POST", self._search_url,
                headers=self._headers(), json=body,
                cache_key=f"prospeo:search:{domain}:p{page}",
                cache_ttl=self._s.cache_ttl_seconds,
            )
            pagination = payload.get("pagination", {}) if isinstance(payload, dict) else {}
            total_pages = int(pagination.get("total_page", page) or page)
            rows = as_list(payload, ("results", "response.results", "data.results", "people"))
            if not rows:
                break

            for row in rows:
                # each result = {"person": {...}, "company": {...}}
                person = row.get("person") if isinstance(row.get("person"), dict) else row
                li = first(person, ("linkedin_url", "linkedin", "linkedin_profile"))
                li_key = (li or "").strip().lower().rstrip("/")
                if li_key:
                    if li_key in seen_li:
                        continue
                    seen_li.add(li_key)
                out.append(self._to_contact(person, domain, li))
                if len(out) >= limit:
                    break
            page += 1

        log.info("Prospeo: %d contacts for %s", len(out), domain)
        return out

    def _to_contact(self, person: dict, domain: str, li: str | None) -> Contact:
        # current title/seniority/department live in the active job_history entry
        seniority = department = None
        for job in person.get("job_history", []) or []:
            if isinstance(job, dict) and job.get("current"):
                seniority = job.get("seniority")
                deps = job.get("departments")
                department = deps[0] if isinstance(deps, list) and deps else deps
                break
        # search sometimes already returns the verified email object — capture it
        # so Stage 3 can skip a redundant (paid) enrich call.
        email_obj = parse_email_object(person.get("email"))
        return Contact(
            company_domain=domain,
            full_name=first(person, ("full_name", "name")),
            first_name=first(person, ("first_name", "firstname", "given_name")),
            last_name=first(person, ("last_name", "lastname", "family_name")),
            title=first(person, ("current_job_title", "job_title", "title", "headline")),
            seniority=seniority,
            department=department,
            linkedin_url=li,
            email=email_obj,
            email_hint=email_obj.address if email_obj else None,
            raw=person,
        )

    # ── Stage 3 fallback resolver ────────────────────────────────────
    async def resolve_email(self, linkedin_url: str) -> Email | None:
        if not linkedin_url:
            return None
        body = {"data": {"linkedin_url": linkedin_url}}
        payload = await self._http.request_json(
            self.provider, "POST", self._enrich_url,
            headers=self._headers(), json=body,
            cache_key=f"prospeo:enrich:{linkedin_url.strip().lower()}",
            cache_ttl=self._s.cache_ttl_seconds,
        )
        # enrich response: {"person": {..., "email": {"email","status","verification_method"}}}
        node = payload.get("person", payload) if isinstance(payload, dict) else {}
        em = node.get("email") if isinstance(node, dict) else None
        return parse_email_object(em)


def parse_email_object(em) -> Email | None:
    """Build an Email from Prospeo's email object (dict) or a bare string.

    Search returns *masked* previews (`revealed:false`, e.g. `d****@acme.com`);
    those are not sendable, so we drop them and let Stage 3 enrich reveal the
    real address.
    """
    if isinstance(em, dict):
        addr = em.get("email") or em.get("address")
        if not addr or "@" not in str(addr):
            return None
        if em.get("revealed") is False or "*" in str(addr):
            return None  # masked preview — reveal via enrich (Stage 3)
        return Email(
            address=str(addr),
            status=_map_status(str(em.get("status", "UNKNOWN"))),
            verification_method=em.get("verification_method"),
            raw=em,
        )
    if isinstance(em, str) and "@" in em:
        return Email(address=em, status=EmailStatus.UNKNOWN, verification_method="prospect-hint")
    return None


def _map_status(raw: str) -> EmailStatus:
    raw = raw.upper()
    if "VALID" in raw or "VERIFIED" in raw or "DELIVERABLE" in raw:
        return EmailStatus.VERIFIED
    if "RISK" in raw or "ACCEPT_ALL" in raw or "CATCH" in raw:
        return EmailStatus.RISKY
    if "INVALID" in raw or "UNDELIVERABLE" in raw:
        return EmailStatus.INVALID
    if "NOT_FOUND" in raw or "NONE" in raw:
        return EmailStatus.NOT_FOUND
    return EmailStatus.UNKNOWN

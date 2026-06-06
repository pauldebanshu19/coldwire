"""Deterministic fake providers for `--mock` runs: full end-to-end pipeline,
zero credits, no real emails sent. Used for demos, tests, and load stubs.
"""

from __future__ import annotations

import asyncio
import hashlib
from email.utils import make_msgid

from ..config import Settings
from ..logging import get_logger, redact_email
from ..models import Company, Contact, Email, EmailStatus

log = get_logger("mock")

_FIRST = ["Ava", "Noah", "Mia", "Liam", "Zoe", "Kai", "Ivy", "Leo", "Nora", "Eli"]
_LAST = ["Stone", "Vega", "Lane", "Reyes", "Cole", "Frost", "Wells", "Hart", "Diaz", "Knox"]
_TITLES = ["CEO", "CTO", "VP Sales", "VP Marketing", "Chief Revenue Officer", "Head of Growth"]
_INDUSTRIES = ["SaaS", "Fintech", "Logistics", "Healthtech", "E-commerce"]


def _h(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


class MockOceanClient:
    def __init__(self, settings: Settings) -> None:
        self._s = settings

    async def find_lookalikes(self, seed_domain: str) -> list[Company]:
        await asyncio.sleep(0.05)
        n = min(self._s.max_companies, 8)
        base = seed_domain.split(".")[0]
        out = []
        for i in range(n):
            h = _h(f"{seed_domain}:{i}")
            out.append(Company(
                domain=f"{base}-rival{i+1}.com",
                name=f"{base.capitalize()} Rival {i+1}",
                size=str(50 + h % 950),
                industry=_INDUSTRIES[h % len(_INDUSTRIES)],
                country="US",
                raw={"mock": True},
            ))
        log.info("Ocean[mock]: %d companies", len(out))
        return out


class MockProspeoClient:
    def __init__(self, settings: Settings) -> None:
        self._s = settings

    async def find_contacts(self, domain: str) -> list[Contact]:
        await asyncio.sleep(0.04)
        n = min(self._s.max_contacts_per_company, 3)
        out = []
        for i in range(n):
            h = _h(f"{domain}:{i}")
            fn, ln = _FIRST[h % len(_FIRST)], _LAST[(h // 7) % len(_LAST)]
            out.append(Contact(
                company_domain=domain,
                first_name=fn, last_name=ln, full_name=f"{fn} {ln}",
                title=_TITLES[h % len(_TITLES)],
                seniority="C-Level" if i == 0 else "VP",
                linkedin_url=f"https://www.linkedin.com/in/{fn.lower()}-{ln.lower()}-{h % 9999}",
                raw={"mock": True},
            ))
        return out


class MockResolver:
    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    async def resolve_email(self, linkedin_url: str) -> Email | None:
        await asyncio.sleep(0.03)
        h = _h(linkedin_url)
        if h % 7 == 0:  # ~1 in 7 unresolvable, to exercise skip handling
            return None
        slug = linkedin_url.rstrip("/").split("/")[-1].split("-")
        local = f"{slug[0]}.{slug[1]}" if len(slug) > 1 else slug[0]
        status = EmailStatus.VERIFIED if h % 3 else EmailStatus.RISKY
        return Email(address=f"{local}@example-mock.com", status=status,
                     verification_method="mock", raw={"mock": True})


class MockBrevoClient:
    transport = "mock"

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    async def send(self, *, to_email, to_name, subject, html, text, unsubscribe_url=None) -> str:
        await asyncio.sleep(0.03)
        mid = make_msgid().strip("<>")
        log.info("Brevo[mock]: would send to %s (msg %s)", redact_email(to_email), mid)
        return mid

"""Stage 2 — find decision-makers per company (concurrent, deduped).

A company with no contacts yields zero and the run moves on; one company's
failure never sinks the rest.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..errors import ProviderError
from ..events import EventFn, emit
from ..logging import get_logger
from ..models import Company, Contact

log = get_logger("stage.prospect")


async def find_contacts(
    prospeo,
    companies: list[Company],
    concurrency: int = 5,
    on_event: Optional[EventFn] = None,
) -> list[Contact]:
    emit(on_event, "prospeo", "start", 0, f"Prospecting {len(companies)} companies")
    sem = asyncio.Semaphore(max(concurrency, 1))
    contacts: list[Contact] = []
    seen: set[str] = set()

    async def one(company: Company) -> list[Contact]:
        async with sem:
            try:
                return await prospeo.find_contacts(company.domain)
            except ProviderError as exc:
                log.warning("prospect failed for %s: %s", company.domain, exc)
                emit(on_event, "prospeo", "skip", 0, f"{company.domain}: {exc}")
                return []

    for batch in await asyncio.gather(*(one(c) for c in companies)):
        for contact in batch:
            if contact.dedup_key in seen:
                continue
            seen.add(contact.dedup_key)
            contacts.append(contact)
            emit(on_event, "prospeo", "progress", len(contacts),
                 f"{contact.display_name} · {contact.title or '?'} @ {contact.company_domain}")

    emit(on_event, "prospeo", "done", len(contacts), f"{len(contacts)} unique contacts")
    return contacts

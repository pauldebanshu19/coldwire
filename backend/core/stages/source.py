"""Stage 1 — source lookalike companies from one seed domain."""

from __future__ import annotations

from typing import Optional

from ..events import EventFn, emit
from ..logging import get_logger
from ..models import Company

log = get_logger("stage.source")


async def source_companies(ocean, seed_domain: str, on_event: Optional[EventFn] = None) -> list[Company]:
    emit(on_event, "ocean", "start", 0, f"Sourcing lookalikes for {seed_domain}")
    companies = await ocean.find_lookalikes(seed_domain)
    emit(on_event, "ocean", "done", len(companies), f"{len(companies)} lookalike companies")
    return companies

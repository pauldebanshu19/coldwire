"""Stage 3 — resolve LinkedIn URLs to verified work emails (concurrent).

A contact whose email won't resolve is recorded as skipped (email stays None),
excluded from the send count, and surfaced in the summary — never crashes the run.
Falls back to any email hint the prospecting provider already returned.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..errors import ProviderError
from ..events import EventFn, emit
from ..logging import get_logger, redact_email
from ..models import Contact, Email, EmailStatus

log = get_logger("stage.resolve")


async def resolve_emails(
    resolver,
    contacts: list[Contact],
    concurrency: int = 5,
    on_event: Optional[EventFn] = None,
) -> list[Contact]:
    emit(on_event, "resolve", "start", 0, f"Resolving emails for {len(contacts)} contacts")
    sem = asyncio.Semaphore(max(concurrency, 1))
    resolved = 0

    async def one(contact: Contact) -> None:
        nonlocal resolved
        async with sem:
            # Already verified upstream (e.g. Prospeo search returned the email)?
            # Skip the paid resolver call.
            if contact.is_deliverable:
                resolved += 1
                emit(on_event, "resolve", "progress", resolved,
                     f"{contact.display_name} -> {redact_email(contact.email.address)} (cached)")
                return
            email: Email | None = None
            if contact.linkedin_url:
                try:
                    email = await resolver.resolve_email(contact.linkedin_url)
                except ProviderError as exc:
                    log.warning("resolve failed for %s: %s", contact.display_name, exc)
                    emit(on_event, "resolve", "skip", 0, f"{contact.display_name}: {exc}")
            if email is None and contact.email_hint and "@" in contact.email_hint:
                email = Email(address=contact.email_hint, status=EmailStatus.UNKNOWN,
                              verification_method="prospect-hint")
            contact.email = email
            if contact.is_deliverable:
                resolved += 1
                emit(on_event, "resolve", "progress", resolved,
                     f"{contact.display_name} -> {redact_email(contact.email.address)}")
            else:
                emit(on_event, "resolve", "skip", resolved,
                     f"{contact.display_name}: no deliverable email")

    await asyncio.gather(*(one(c) for c in contacts))
    emit(on_event, "resolve", "done", resolved, f"{resolved} deliverable emails")
    return contacts

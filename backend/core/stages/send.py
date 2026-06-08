"""Stage 4 — send personalized outreach (concurrent, idempotent, deduped).

Never mails the same human twice in one run (dedup on resolved email). A
per-send failure is recorded and the run continues.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..config import Settings
from ..errors import ProviderError
from ..events import EventFn, emit
from ..logging import get_logger, redact_email
from ..models import Contact, SendResult, SendStatus
from ..outreach import render, unsubscribe_url

log = get_logger("stage.send")


def sendable_contacts(contacts: list[Contact]) -> list[Contact]:
    """Deliverable contacts, deduped by email address (one mail per human)."""
    out: list[Contact] = []
    seen: set[str] = set()
    for c in contacts:
        if not c.is_deliverable:
            continue
        addr = c.email.address.lower()
        if addr in seen:
            continue
        seen.add(addr)
        out.append(c)
    return out


async def send_outreach(
    brevo,
    contacts: list[Contact],
    settings: Settings,
    concurrency: int = 3,
    on_event: Optional[EventFn] = None,
    suppression: Optional[set[str]] = None,
    reply_to: Optional[str] = None,
    sender_name: Optional[str] = None,
    redirect_to: Optional[str] = None,
) -> list[SendResult]:
    # per-run overrides, else the configured defaults — never mutate settings
    reply = reply_to or settings.reply_to_email or None
    sname = sender_name or settings.sender_name or None
    suppression = {s.lower() for s in (suppression or set())}
    targets = sendable_contacts(contacts)
    skipped = [c for c in contacts if c not in targets]

    results: list[SendResult] = []
    for c in skipped:
        results.append(SendResult(
            contact_name=c.display_name,
            email=c.email.address if c.email else None,
            status=SendStatus.SKIPPED,
            skipped_reason="no deliverable email or duplicate",
        ))

    emit(on_event, "brevo", "start", 0, f"Sending to {len(targets)} contacts")
    sem = asyncio.Semaphore(max(concurrency, 1))
    sent = 0
    lock = asyncio.Lock()

    async def one(contact: Contact) -> SendResult:
        nonlocal sent
        addr = contact.email.address
        if addr.lower() in suppression:
            return SendResult(contact_name=contact.display_name, email=addr,
                              status=SendStatus.SKIPPED, skipped_reason="suppressed/unsubscribed")
        subject, html, text = render(contact, settings)
        async with sem:
            try:
                mid = await brevo.send(
                    to_email=addr, to_name=contact.display_name,
                    subject=subject, html=html, text=text,
                    unsubscribe_url=unsubscribe_url(settings, addr),
                    reply_to=reply, sender_name=sname, redirect_to=redirect_to,
                )
            except ProviderError as exc:
                log.error("send failed for %s: %s", redact_email(addr), exc)
                emit(on_event, "brevo", "error", sent, f"{contact.display_name}: {exc}")
                return SendResult(contact_name=contact.display_name, email=addr,
                                  status=SendStatus.FAILED, error=str(exc))
        async with lock:
            sent += 1
            emit(on_event, "brevo", "progress", sent, f"sent to {contact.display_name}")
        return SendResult(contact_name=contact.display_name, email=addr,
                          status=SendStatus.SENT, message_id=mid)

    results.extend(await asyncio.gather(*(one(c) for c in targets)))
    emit(on_event, "brevo", "done", sent, f"{sent} emails sent")
    return results

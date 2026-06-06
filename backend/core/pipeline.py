"""Orchestrates the four stages with the hard approval gate in the middle.

    source -> prospect -> resolve -> [AWAITING_APPROVAL] -> send

The same function backs both the CLI (terminal y/N prompt) and, later, the
Celery worker (web approval). `approve` is a callback given the Review summary;
returning False (or omitting it) sends nothing.
"""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable, Optional, Union

from .clients import build_clients
from .config import Settings
from .errors import ProviderError
from .events import EventFn, emit
from .logging import get_logger
from .models import PipelineResult, Review, utcnow
from .outreach import render
from .stages.prospect import find_contacts
from .stages.resolve import resolve_emails
from .stages.send import sendable_contacts, send_outreach
from .stages.source import source_companies

log = get_logger("pipeline")

ApproveFn = Callable[[Review], Union[bool, Awaitable[bool]]]


def build_review(seed: str, result: PipelineResult, settings: Settings) -> Review:
    sendable = sendable_contacts(result.contacts)
    sample_to = sample_subject = sample_body = None
    if sendable:
        subj, _html, text = render(sendable[0], settings)
        sample_to = sendable[0].email.address
        sample_subject, sample_body = subj, text
    return Review(
        seed_domain=seed,
        companies=len(result.companies),
        contacts=len(result.contacts),
        deliverable=len(sendable),
        skipped=len(result.contacts) - len(sendable),
        sample_to=sample_to,
        sample_subject=sample_subject,
        sample_body=sample_body,
        sendable=sendable,
    )


async def _approved(approve: Optional[ApproveFn], review: Review) -> bool:
    if approve is None:
        log.warning("No approver supplied — defaulting to CANCELLED (nothing sent)")
        return False
    res = approve(review)
    if inspect.isawaitable(res):
        res = await res
    return bool(res)


async def run_pipeline(
    settings: Settings,
    seed_domain: str,
    *,
    on_event: Optional[EventFn] = None,
    approve: Optional[ApproveFn] = None,
    suppression: Optional[set[str]] = None,
) -> PipelineResult:
    result = PipelineResult(seed_domain=seed_domain, status="QUEUED")
    try:
        async with build_clients(settings) as clients:
            # Stage 1
            result.status = "SOURCING"
            result.companies = await source_companies(clients.ocean, seed_domain, on_event)
            if not result.companies:
                result.status = "COMPLETED"
                result.error = "No lookalike companies returned for seed domain"
                emit(on_event, "pipeline", "done", 0, result.error)
                return _finish(result)

            # Stage 2
            result.status = "PROSPECTING"
            result.contacts = await find_contacts(
                clients.prospeo, result.companies, settings.prospect_concurrency, on_event
            )

            # Stage 3
            result.status = "RESOLVING"
            result.contacts = await resolve_emails(
                clients.resolver, result.contacts, settings.resolve_concurrency, on_event
            )

            # ── Approval gate (HARD STOP) ──
            result.status = "AWAITING_APPROVAL"
            review = build_review(seed_domain, result, settings)
            emit(on_event, "pipeline", "progress", review.deliverable,
                 f"Awaiting approval — {review.deliverable} deliverable, {review.skipped} skipped")

            if not await _approved(approve, review):
                result.status = "CANCELLED"
                emit(on_event, "pipeline", "done", 0, "Cancelled — zero emails sent")
                return _finish(result)

            # Stage 4
            result.status = "SENDING"
            result.results = await send_outreach(
                clients.brevo, result.contacts, settings,
                settings.send_concurrency, on_event, suppression,
            )
            result.status = "COMPLETED"
            emit(on_event, "pipeline", "done", result.stats["sent"],
                 f"Completed — {result.stats['sent']} sent, {result.stats['failed']} failed")
            return _finish(result)

    except ProviderError as exc:
        log.exception("pipeline failed")
        result.status = "FAILED"
        result.error = f"{exc.provider or 'provider'}: {exc}"
        emit(on_event, "pipeline", "error", 0, result.error)
        return _finish(result)
    except Exception as exc:  # noqa: BLE001 - top-level guard, never crash the run
        log.exception("pipeline crashed")
        result.status = "FAILED"
        result.error = str(exc)
        emit(on_event, "pipeline", "error", 0, result.error)
        return _finish(result)


def _finish(result: PipelineResult) -> PipelineResult:
    result.finished_at = utcnow()
    return result

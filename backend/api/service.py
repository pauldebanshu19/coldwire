"""Job orchestration + persistence.

Reuses the Phase-1 engine's stage functions unchanged. The web flow splits the
pipeline across the approval gate:

  run_job_async   : Stage 1->2->3, persist everything, stop at AWAITING_APPROVAL
  (user approves)
  run_send_async  : Stage 4, idempotent send, COMPLETED

Both run as either a Celery task (Redis set) or an in-process asyncio task.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.clients import build_clients
from core.config import Settings
from core.models import Contact as CoreContact, Email as CoreEmail, EmailStatus, normalize_domain
from core.outreach import render
from core.stages.prospect import find_contacts
from core.stages.resolve import resolve_emails
from core.stages.send import sendable_contacts, send_outreach
from core.stages.source import source_companies

from db.models import Company, Contact, Email, Job, Outreach, User
from db.session import AsyncSessionLocal
from .events import get_bus
from .schemas import ResultRow, ResultsOut, ReviewOut


def _now() -> datetime:
    return datetime.now(timezone.utc)


def core_settings() -> Settings:
    """Fresh engine settings from env/.env (provider keys, mock, limits)."""
    return Settings()


def _make_emit(bus, job_id: str):
    def emit(stage: str, status: str, count: int, message: str) -> None:
        bus.publish_nowait(job_id, {"stage": stage, "status": status,
                                    "count": count, "message": message})
    return emit


_TERMINAL = {"COMPLETED", "CANCELLED", "FAILED"}


async def _set_status(session: AsyncSession, job: Job, status: str, bus, *,
                      stats: dict | None = None, error: str | None = None) -> None:
    job.status = status
    if stats is not None:
        job.stats = stats
    if error is not None:
        job.error = error
    if status in _TERMINAL:
        job.completed_at = _now()
    await session.commit()
    pstatus = "error" if status == "FAILED" else ("done" if status in _TERMINAL else "progress")
    bus.publish_nowait(job.id, {"stage": "pipeline", "status": pstatus,
                                "count": 0, "message": status, "job_status": status})


# ── Job creation / queries ───────────────────────────────────────────
async def create_job(session: AsyncSession, user: User, seed_domain: str,
                     idem_key: str | None) -> tuple[Job, bool]:
    if idem_key:
        existing = (await session.execute(
            select(Job).where(Job.user_id == user.id, Job.idempotency_key == idem_key)
        )).scalar_one_or_none()
        if existing:
            return existing, False
    job = Job(user_id=user.id, seed_domain=normalize_domain(seed_domain),
              idempotency_key=idem_key, status="QUEUED", stats={})
    session.add(job)
    await session.commit()
    return job, True


# ── Stage 1-3 ─────────────────────────────────────────────────────────
async def run_job_async(job_id: str) -> None:
    settings = core_settings()
    bus = get_bus()
    emit = _make_emit(bus, job_id)
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None or job.status not in ("QUEUED",):
            return
        try:
            await _set_status(session, job, "SOURCING", bus)
            async with build_clients(settings) as clients:
                companies = await source_companies(clients.ocean, job.seed_domain, emit)
                domain_to_cid = await _save_companies(session, job, companies)
                await _set_status(session, job, "PROSPECTING", bus,
                                  stats={"companies": len(companies)})

                contacts = await find_contacts(
                    clients.prospeo, companies, settings.prospect_concurrency, emit)
                cid_by_key = await _save_contacts(session, job, contacts, domain_to_cid)
                await _set_status(session, job, "RESOLVING", bus,
                                  stats={"companies": len(companies), "contacts": len(contacts)})

                contacts = await resolve_emails(
                    clients.resolver, contacts, settings.resolve_concurrency, emit)
                await _save_emails(session, contacts, cid_by_key)

            sendable = sendable_contacts(contacts)
            stats = {"companies": len(companies), "contacts": len(contacts),
                     "deliverable": len(sendable), "skipped": len(contacts) - len(sendable)}
            await _set_status(session, job, "AWAITING_APPROVAL", bus, stats=stats)
        except Exception as exc:  # noqa: BLE001 — never crash the worker
            await session.rollback()
            job = await session.get(Job, job_id)
            if job:
                await _set_status(session, job, "FAILED", bus, error=str(exc))


# ── Stage 4 ───────────────────────────────────────────────────────────
async def run_send_async(job_id: str) -> None:
    settings = core_settings()
    bus = get_bus()
    emit = _make_emit(bus, job_id)
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None or job.status != "SENDING":
            return
        try:
            rows, contact_by_addr = await _load_sendable(session, job_id)
            results = []
            if rows:
                async with build_clients(settings) as clients:
                    results = await send_outreach(
                        clients.brevo, rows, settings, settings.send_concurrency, emit)
                await _save_outreach(session, job_id, results, contact_by_addr)
            sent = sum(1 for r in results if r.status.value == "SENT")
            failed = sum(1 for r in results if r.status.value == "FAILED")
            stats = {**(job.stats or {}), "sent": sent, "failed": failed}
            await _set_status(session, job, "COMPLETED", bus, stats=stats)
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            job = await session.get(Job, job_id)
            if job:
                await _set_status(session, job, "FAILED", bus, error=str(exc))


# ── Review (approval gate payload) ───────────────────────────────────
async def build_review(session: AsyncSession, job: Job) -> ReviewOut:
    rows, _ = await _load_sendable(session, job.id)
    n_companies = len((await session.execute(
        select(Company.id).where(Company.job_id == job.id))).all())
    n_contacts = len((await session.execute(
        select(Contact.id).where(Contact.job_id == job.id))).all())
    sendable = sendable_contacts(rows)
    sample_to = sample_subject = sample_body = template_subject = None
    if sendable:
        subj, _html, text = render(sendable[0], core_settings())
        sample_to, sample_subject, sample_body, template_subject = \
            sendable[0].email.address, subj, text, subj
    return ReviewOut(
        job_id=job.id, status=job.status,
        companies=n_companies, contacts=n_contacts,
        deliverable=len(sendable), skipped=n_contacts - len(sendable),
        template_subject=template_subject, sample_to=sample_to,
        sample_subject=sample_subject, sample_body=sample_body,
    )


async def build_results(session: AsyncSession, job: Job) -> ResultsOut:
    stmt = (select(Outreach, Contact, Email.address)
            .join(Contact, Contact.id == Outreach.contact_id)
            .join(Email, Email.contact_id == Contact.id, isouter=True)
            .where(Outreach.job_id == job.id))
    rows = (await session.execute(stmt)).all()
    out = [ResultRow(contact=c.full_name or c.linkedin_url or "Unknown", email=addr,
                     status=o.status, message_id=o.brevo_message_id, error=o.error)
           for o, c, addr in rows]
    return ResultsOut(job_id=job.id, status=job.status, stats=job.stats or {}, results=out)


# ── Persistence helpers ───────────────────────────────────────────────
async def _save_companies(session, job, companies) -> dict[str, str]:
    mapping: dict[str, Company] = {}
    for comp in companies:
        row = Company(job_id=job.id, domain=comp.domain, name=comp.name, size=comp.size,
                      industry=comp.industry, country=comp.country, raw=comp.raw)
        session.add(row)
        mapping[comp.domain] = row
    await session.flush()
    return {d: r.id for d, r in mapping.items()}


async def _save_contacts(session, job, contacts, domain_to_cid) -> dict[str, str]:
    out: dict[str, Contact] = {}
    for cc in contacts:
        cid = domain_to_cid.get(cc.company_domain)
        if not cid:
            continue
        row = Contact(company_id=cid, job_id=job.id, full_name=cc.full_name,
                      first_name=cc.first_name, last_name=cc.last_name, title=cc.title,
                      seniority=cc.seniority, department=cc.department,
                      linkedin_url=cc.linkedin_url, raw=cc.raw)
        session.add(row)
        out[cc.dedup_key] = row
    await session.flush()
    return {k: r.id for k, r in out.items()}


async def _save_emails(session, contacts, cid_by_key) -> None:
    for cc in contacts:
        if cc.email is None:
            continue
        cid = cid_by_key.get(cc.dedup_key)
        if not cid:
            continue
        session.add(Email(
            contact_id=cid, address=cc.email.address,
            verification_status=cc.email.status.value,
            deliverable=cc.email.deliverable,
            verification_method=cc.email.verification_method,
        ))
    await session.commit()


async def _load_sendable(session, job_id) -> tuple[list[CoreContact], dict[str, Contact]]:
    """Deliverable contacts as core models, excluding already-sent (idempotency)."""
    sent_ids = set((await session.execute(
        select(Outreach.contact_id).where(
            Outreach.job_id == job_id, Outreach.status == "SENT"))
    ).scalars().all())

    stmt = (select(Contact, Email, Company.domain)
            .join(Email, Email.contact_id == Contact.id)
            .join(Company, Company.id == Contact.company_id)
            .where(Contact.job_id == job_id, Email.deliverable.is_(True)))
    core_list: list[CoreContact] = []
    by_addr: dict[str, Contact] = {}
    for contact, email, domain in (await session.execute(stmt)).all():
        if contact.id in sent_ids:
            continue
        try:
            status = EmailStatus(email.verification_status)
        except ValueError:
            status = EmailStatus.UNKNOWN
        core = CoreContact(
            company_domain=domain, full_name=contact.full_name,
            first_name=contact.first_name, last_name=contact.last_name,
            title=contact.title, seniority=contact.seniority,
            linkedin_url=contact.linkedin_url,
            email=CoreEmail(address=email.address, status=status,
                            verification_method=email.verification_method),
        )
        core_list.append(core)
        by_addr[email.address.lower()] = contact
    return core_list, by_addr


async def _save_outreach(session, job_id, results, contact_by_addr) -> None:
    for r in results:
        if not r.email:
            continue
        contact = contact_by_addr.get(r.email.lower())
        if contact is None:
            continue
        idem = f"{job_id}:{contact.id}"
        existing = (await session.execute(
            select(Outreach).where(Outreach.idempotency_key == idem))).scalar_one_or_none()
        if existing is None:
            existing = Outreach(job_id=job_id, contact_id=contact.id, idempotency_key=idem)
            session.add(existing)
        existing.status = r.status.value
        existing.brevo_message_id = r.message_id
        existing.error = r.error
        if r.status.value == "SENT":
            existing.sent_at = _now()
    await session.commit()

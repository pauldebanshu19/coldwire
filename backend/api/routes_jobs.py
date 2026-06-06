"""Jobs API — submit, status, SSE progress, review, approve/cancel, results
(PRD §8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Job, User
from db.session import AsyncSessionLocal
from .deps import get_current_user, get_session
from .dispatch import dispatch_run_job, dispatch_send
from .events import format_sse, get_bus
from .schemas import JobIn, JobOut, ResultsOut, ReviewOut
from .security import decode_token
from .service import build_results, build_review, create_job, _set_status

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# states from which a job may still be cancelled (before/at the gate)
_CANCELLABLE = {"QUEUED", "SOURCING", "PROSPECTING", "RESOLVING", "AWAITING_APPROVAL"}


def _to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id, seed_domain=job.seed_domain, status=job.status,
        stats=job.stats or {}, error=job.error,
        created_at=job.created_at, approved_at=job.approved_at,
        completed_at=job.completed_at,
    )


async def _owned(session: AsyncSession, user: User, job_id: str) -> Job:
    job = await session.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post("", response_model=JobOut, status_code=202)
async def submit_job(
    body: JobIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobOut:
    job, created = await create_job(session, user, body.seed_domain, idempotency_key)
    if created:
        dispatch_run_job(job.id)
    return _to_out(job)


@router.get("", response_model=list[JobOut])
async def list_jobs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[JobOut]:
    rows = (await session.execute(
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()))
    ).scalars().all()
    return [_to_out(j) for j in rows]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: User = Depends(get_current_user),
                  session: AsyncSession = Depends(get_session)) -> JobOut:
    return _to_out(await _owned(session, user, job_id))


@router.get("/{job_id}/review", response_model=ReviewOut)
async def review(job_id: str, user: User = Depends(get_current_user),
                 session: AsyncSession = Depends(get_session)) -> ReviewOut:
    return await build_review(session, await _owned(session, user, job_id))


@router.post("/{job_id}/approve", response_model=JobOut)
async def approve(job_id: str, user: User = Depends(get_current_user),
                  session: AsyncSession = Depends(get_session)) -> JobOut:
    job = await _owned(session, user, job_id)
    if job.status != "AWAITING_APPROVAL":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot approve from {job.status}")
    from .service import _now
    job.approved_at = _now()
    await _set_status(session, job, "SENDING", get_bus())
    dispatch_send(job.id)
    return _to_out(job)


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel(job_id: str, user: User = Depends(get_current_user),
                 session: AsyncSession = Depends(get_session)) -> JobOut:
    job = await _owned(session, user, job_id)
    if job.status not in _CANCELLABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot cancel from {job.status}")
    await _set_status(session, job, "CANCELLED", get_bus())
    return _to_out(job)


@router.get("/{job_id}/results", response_model=ResultsOut)
async def results(job_id: str, user: User = Depends(get_current_user),
                  session: AsyncSession = Depends(get_session)) -> ResultsOut:
    return await build_results(session, await _owned(session, user, job_id))


@router.get("/{job_id}/events")
async def events(job_id: str, token: str = Query(default="")):
    """SSE progress stream. EventSource can't set headers, so the JWT comes as
    a `?token=` query param."""
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None or job.user_id != user_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    bus = get_bus()

    async def gen():
        # replay history, then live tail (stream replays from start for both buses)
        async for event in bus.stream(job_id):
            yield format_sse(event)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "Connection": "keep-alive",
                                      "X-Accel-Buffering": "no",
                                      # token rides the query string (EventSource
                                      # can't set headers) — don't leak it via Referer
                                      "Referrer-Policy": "no-referrer"})

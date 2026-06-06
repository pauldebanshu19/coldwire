"""Celery tasks wrapping the async service functions (one asyncio loop per task)."""

from __future__ import annotations

import asyncio

from .celery_app import celery


@celery.task(name="run_job", bind=True, max_retries=3)
def run_job_task(self, job_id: str) -> None:
    from api.service import run_job_async
    asyncio.run(run_job_async(job_id))


@celery.task(name="run_send", bind=True, max_retries=3)
def run_send_task(self, job_id: str) -> None:
    from api.service import run_send_async
    asyncio.run(run_send_async(job_id))

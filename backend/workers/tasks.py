"""Celery tasks wrapping the async service functions (one asyncio loop per task).

A task that exhausts retries or crashes lands in a Redis **dead-letter list**
(`coldwire:dlq`) for inspection instead of vanishing. (Business-level failures
are already recorded durably as FAILED jobs in Postgres by the service.)
"""

from __future__ import annotations

import asyncio
import json
import time

from celery import Task

from app_settings import get_app_settings
from .celery_app import celery


class DLQTask(Task):
    """Base task that records terminal failures to a Redis dead-letter list."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: ANN001
        settings = get_app_settings()
        if not settings.redis_url:
            return
        try:
            import redis  # sync client (we're in a worker thread)
            r = redis.from_url(settings.redis_url)
            r.rpush("coldwire:dlq", json.dumps({
                "task": self.name, "task_id": task_id,
                "args": list(args), "error": str(exc), "ts": time.time(),
            }))
            r.ltrim("coldwire:dlq", -1000, -1)  # keep the last 1000
        except Exception:  # noqa: BLE001 - DLQ must never raise
            pass


@celery.task(name="run_job", base=DLQTask, bind=True, max_retries=3)
def run_job_task(self, job_id: str) -> None:
    from api.service import run_job_async
    asyncio.run(run_job_async(job_id))


@celery.task(name="run_send", base=DLQTask, bind=True, max_retries=3)
def run_send_task(self, job_id: str) -> None:
    from api.service import run_send_async
    asyncio.run(run_send_async(job_id))

"""Enqueue abstraction.

  Redis configured -> Celery task (real queue, separate worker pool)
  otherwise        -> in-process asyncio task (zero-infra local demo)

Both paths execute the same async service functions.
"""

from __future__ import annotations

import asyncio

from app_settings import get_app_settings

_background: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    task = asyncio.ensure_future(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)


def dispatch_run_job(job_id: str) -> None:
    if get_app_settings().use_celery:
        from workers.tasks import run_job_task
        run_job_task.delay(job_id)
    else:
        from .service import run_job_async
        _spawn(run_job_async(job_id))


def dispatch_send(job_id: str) -> None:
    if get_app_settings().use_celery:
        from workers.tasks import run_send_task
        run_send_task.delay(job_id)
    else:
        from .service import run_send_async
        _spawn(run_send_async(job_id))

"""Celery application. Broker/backend come from REDIS_URL; falls back to eager
(in-process) execution when Redis is not configured.
"""

from __future__ import annotations

from celery import Celery

from app_settings import get_app_settings

_s = get_app_settings()

celery = Celery("coldwire", broker=_s.broker_url, backend=_s.result_backend)
celery.conf.update(
    task_always_eager=not _s.use_celery,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,                # redeliver if a worker dies mid-task
    worker_prefetch_multiplier=1,       # fair dispatch across workers
    task_default_retry_delay=5,
    task_track_started=True,
)

# register tasks
from . import tasks  # noqa: E402,F401

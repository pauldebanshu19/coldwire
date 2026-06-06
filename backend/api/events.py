"""Progress event bus + SSE.

The engine's `on_event` is a *sync* callback, so the bus exposes a sync
`publish_nowait`. SSE consumers use the async `stream`, which replays history
then tails live events until a terminal pipeline event.

  • No Redis  -> MemoryBus (process-local; pairs with in-process dispatch)
  • Redis set -> RedisStreamBus (shared across API + Celery workers)
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator, Optional

from app_settings import get_app_settings


def is_terminal(event: dict) -> bool:
    return event.get("stage") == "pipeline" and event.get("status") in ("done", "error")


def format_sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


class MemoryBus:
    def __init__(self) -> None:
        self._events: dict[str, list[dict]] = {}
        self._notify: dict[str, asyncio.Event] = {}

    def _ev(self, job_id: str) -> asyncio.Event:
        return self._notify.setdefault(job_id, asyncio.Event())

    def publish_nowait(self, job_id: str, event: dict) -> None:
        event.setdefault("ts", time.time())
        self._events.setdefault(job_id, []).append(event)
        ev = self._ev(job_id)
        ev.set()

    async def history(self, job_id: str) -> list[dict]:
        return list(self._events.get(job_id, []))

    async def stream(self, job_id: str) -> AsyncIterator[dict]:
        idx = 0
        while True:
            events = self._events.get(job_id, [])
            while idx < len(events):
                event = events[idx]
                idx += 1
                yield event
                if is_terminal(event):
                    return
            ev = self._ev(job_id)
            ev.clear()
            try:
                await asyncio.wait_for(ev.wait(), timeout=15)
            except asyncio.TimeoutError:
                yield {"stage": "heartbeat", "status": "ping", "ts": time.time()}


class RedisStreamBus:
    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(url, decode_responses=True)
        self._tasks: set[asyncio.Task] = set()

    def _key(self, job_id: str) -> str:
        return f"job:{job_id}:events"

    def publish_nowait(self, job_id: str, event: dict) -> None:
        event.setdefault("ts", time.time())
        task = asyncio.ensure_future(self._publish(job_id, event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _publish(self, job_id: str, event: dict) -> None:
        await self._redis.xadd(self._key(job_id), {"e": json.dumps(event)},
                               maxlen=1000, approximate=True)

    async def history(self, job_id: str) -> list[dict]:
        rows = await self._redis.xrange(self._key(job_id))
        return [json.loads(v["e"]) for _, v in rows]

    async def stream(self, job_id: str) -> AsyncIterator[dict]:
        last = "0"
        while True:
            resp = await self._redis.xread({self._key(job_id): last}, block=15000, count=50)
            if not resp:
                yield {"stage": "heartbeat", "status": "ping", "ts": time.time()}
                continue
            for _stream, rows in resp:
                for rid, v in rows:
                    last = rid
                    event = json.loads(v["e"])
                    yield event
                    if is_terminal(event):
                        return


_bus: Optional[object] = None


def get_bus():
    global _bus
    if _bus is None:
        s = get_app_settings()
        _bus = RedisStreamBus(s.redis_url) if s.use_celery else MemoryBus()
    return _bus

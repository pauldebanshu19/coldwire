"""Progress event type shared by CLI (prints) and, later, the SSE stream."""

from __future__ import annotations

from typing import Callable, Optional

# on_event(stage, status, count, message)
#   stage  ∈ ocean | prospeo | eazyreach | brevo | pipeline
#   status ∈ start | progress | done | skip | error
EventFn = Callable[[str, str, int, str], None]


def emit(on_event: Optional[EventFn], stage: str, status: str, count: int, message: str) -> None:
    if on_event is not None:
        on_event(stage, status, count, message)

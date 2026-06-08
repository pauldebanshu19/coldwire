"""Per-provider circuit breakers.

If a provider starts failing consistently, the breaker opens and subsequent
calls fast-fail (CircuitOpenError, a TerminalError) instead of hammering it —
so one dead provider pauses its own stage without torching the whole run. After
a cooldown it half-opens to probe recovery.
"""

from __future__ import annotations

import asyncio
import time

from .errors import TerminalError
from .logging import get_logger

log = get_logger("breaker")


class CircuitOpenError(TerminalError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"{provider} circuit open — provider failing, paused", provider=provider)


class CircuitBreaker:
    def __init__(self, name: str, fail_max: int = 5, reset_timeout: float = 30.0) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at = 0.0
        self._state = "closed"  # closed | open | half_open
        self._lock = asyncio.Lock()

    async def check(self) -> None:
        async with self._lock:
            if self._state == "open":
                if time.monotonic() - self._opened_at >= self.reset_timeout:
                    self._state = "half_open"  # allow a single trial call
                else:
                    raise CircuitOpenError(self.name)

    async def record_success(self) -> None:
        async with self._lock:
            if self._state != "closed":
                log.info("%s circuit closed (recovered)", self.name)
            self._failures = 0
            self._state = "closed"

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._state == "half_open" or self._failures >= self.fail_max:
                if self._state != "open":
                    log.warning("%s circuit OPEN after %d failures", self.name, self._failures)
                self._state = "open"
                self._opened_at = time.monotonic()


class BreakerRegistry:
    def __init__(self, fail_max: int = 5, reset_timeout: float = 30.0) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._fail_max = fail_max
        self._reset_timeout = reset_timeout

    def get(self, name: str) -> CircuitBreaker:
        return self._breakers.setdefault(
            name, CircuitBreaker(name, self._fail_max, self._reset_timeout)
        )

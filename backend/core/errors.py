"""Typed errors so retry logic can distinguish retryable from terminal."""

from __future__ import annotations

from typing import Optional


class ProviderError(Exception):
    """Base for any provider-call failure."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        status: Optional[int] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status = status
        self.retryable = retryable


class RetryableError(ProviderError):
    """429 / 5xx / network timeout — safe to retry with backoff."""

    def __init__(self, message: str, *, provider: str = "", status: Optional[int] = None,
                 retry_after: Optional[float] = None) -> None:
        super().__init__(message, provider=provider, status=status, retryable=True)
        self.retry_after = retry_after


class TerminalError(ProviderError):
    """401 / 400 / 403 — retrying just earns a ban. Fail fast."""

    def __init__(self, message: str, *, provider: str = "", status: Optional[int] = None) -> None:
        super().__init__(message, provider=provider, status=status, retryable=False)


class AuthError(TerminalError):
    """Missing or rejected credentials."""


class ConfigError(Exception):
    """Misconfiguration caught before any network call."""

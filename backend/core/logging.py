"""Structured logging. Never logs full email bodies / PII in plaintext."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s", "%H:%M:%S")
    )
    root = logging.getLogger("coldwire")
    root.setLevel(level.upper())
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"coldwire.{name}")


def redact_email(addr: str | None) -> str:
    """`john.doe@acme.com` -> `j***@acme.com` for safe logging."""
    if not addr or "@" not in addr:
        return "<redacted>"
    local, _, domain = addr.partition("@")
    head = local[0] if local else "?"
    return f"{head}***@{domain}"

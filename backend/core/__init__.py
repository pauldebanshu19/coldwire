"""Coldwire pipeline core — pure Python engine, no web/queue imports.

The CLI and (later) the Celery workers both import from here.
"""

__all__ = ["models", "config", "pipeline"]

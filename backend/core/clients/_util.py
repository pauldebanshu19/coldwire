"""Defensive helpers for parsing provider JSON whose exact shape varies."""

from __future__ import annotations

from typing import Any, Iterable


def first(d: dict, keys: Iterable[str], default: Any = None) -> Any:
    """Return the first present, non-empty value among `keys` (supports `a.b`)."""
    for key in keys:
        val: Any = d
        ok = True
        for part in key.split("."):
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                ok = False
                break
        if ok and val not in (None, "", [], {}):
            return val
    return default


def as_list(payload: Any, keys: Iterable[str]) -> list[dict]:
    """Locate the result array in a response under any of several keys."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        node: Any = payload
        for part in key.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if isinstance(node, list):
            return [x for x in node if isinstance(x, dict)]
    return []

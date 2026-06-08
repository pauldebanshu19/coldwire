"""Test config — force SQLite + mock providers + in-process dispatch before any
app/engine import so the API can be exercised with zero infra and zero credits.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_conduit.db")
os.environ["MOCK"] = "true"
os.environ["REDIS_URL"] = ""          # in-process dispatch + memory bus
os.environ["AUTO_CREATE_TABLES"] = "true"

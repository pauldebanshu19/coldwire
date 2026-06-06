#!/usr/bin/env python3
"""Backend entrypoint — run the API server.

    python main.py                 # http://localhost:8000  (docs at /docs)
    python main.py --port 9000
    python main.py --reload        # auto-reload on code changes (dev)

Env: HOST, PORT, MOCK=true (fake providers / zero credits), DATABASE_URL,
REDIS_URL. With no DATABASE_URL/REDIS_URL it runs on SQLite + in-process tasks —
no Postgres/Redis needed.
"""

from __future__ import annotations

import argparse
import os

import uvicorn

# Expose the FastAPI app so `uvicorn main:app` works:
#     python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
from api.main import app  # noqa: E402,F401


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Conduit backend API")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="auto-reload (dev)")
    args = parser.parse_args()

    print(f"→ Conduit API on http://localhost:{args.port}  (Swagger UI: /docs, health: /health)")
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

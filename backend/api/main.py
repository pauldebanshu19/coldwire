"""FastAPI application — stateless orchestration over the engine."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app_settings import get_app_settings
from db.session import init_models
from .routes_auth import router as auth_router
from .routes_jobs import router as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    if settings.auto_create_tables:
        await init_models()
    yield


app = FastAPI(title="Conduit API", version="0.2.0", lifespan=lifespan)

_settings = get_app_settings()
_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
if _origins:
    # explicit origins -> credentialed CORS is safe
    app.add_middleware(
        CORSMiddleware, allow_origins=_origins, allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
elif _settings.dev_mode:
    # local dev: wildcard WITHOUT credentials (we use bearer tokens, not cookies).
    # Never combine "*" with allow_credentials=True.
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=False,
        allow_methods=["*"], allow_headers=["*"],
    )
else:
    raise RuntimeError("CORS_ORIGINS must be set when DEV_MODE is false")

app.include_router(auth_router)
app.include_router(jobs_router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    s = get_app_settings()
    return {"status": "ok", "queue": "celery" if s.use_celery else "in-process"}

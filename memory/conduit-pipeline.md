---
name: conduit-pipeline
description: Conduit cold-outreach take-home — backend Phase 1 status, provider/key quirks
metadata:
  type: project
---

Take-home "build, then demo": fully automated cold-outreach pipeline. One seed
domain → Ocean.io lookalikes → Prospeo decision-makers → email reveal → approval
gate → Brevo send. Repo `coldwire/`; `PRD.md` is the full plan; build lives in
`backend/`.

**Phase 1 (engine + CLI) DONE & validated live** (stripe.com → razorpay/cashfree
→ real C-suite → revealed emails → gate). Pure engine `backend/core/`, CLI
`backend/cli.py`.

**Phase 2 (FastAPI + Postgres + Celery/Redis) DONE & validated on Docker stack**
(Celery worker processed job cross-process, SSE via Redis Streams, 15 SENT rows
in Postgres). `backend/api/` (JWT auth, jobs, SSE), `backend/db/` (async
SQLAlchemy), `backend/workers/` (celery), `docker-compose.yml`. Key design:
all-async DB; `REDIS_URL` set → Celery + RedisStreamBus, unset → in-process
asyncio + MemoryBus (zero-infra local). `NullPool` required (asyncpg + per-task
event loops). Engine reused untouched; pipeline split across the gate (run_job
stages 1-3, run_send stage 4). 20 tests pass.

**Phase 3 (Next.js frontend) DONE.** `frontend/` = Next.js 16 + React 19 + Tailwind
v4 + shadcn (radix-nova), bun. Screens: landing/auth (JWT), dashboard (submit +
history), job detail (live SSE pipeline timeline + approval gate + results + CSV).
Client `NEXT_PUBLIC_API_URL`→backend; SSE via EventSource `?token=` (EventSource
can't set headers). Dark "mission-control" theme (lime on near-black, IBM Plex Mono).
`bun run build` green (deleted unused scaffold ui calendar/chart/carousel — broke vs
react-day-picker v10 / recharts 3). CORS verified cross-origin :3000→:8000.
Backend CORS fixed: never `*`+credentials; fail-closed when DEV_MODE=false.
Single consolidated `backend/requirements.txt`. Run backend: `python main.py` or
`uvicorn main:app`. Next: Phase 4 hardening, Phase 5 scale.

Provider quirks that bit us (now handled in code):
- **Prospeo** search returns **masked** emails (`revealed:false`); must call
  `enrich-person` to reveal — that's the paid Stage-3 reveal. Strict rate limit → 429s, absorbed by retry.
- **Eazyreach** key still PENDING (user will provide). Until then Stage 3 falls
  back to Prospeo `enrich-person`. Endpoint isolated in `clients/eazyreach.py`.
- **Brevo** key the user gave is an SMTP key (`xsmtpsib-…`), not the REST API v3
  key (`xkeysib-…`). So `BREVO_TRANSPORT=auto` selects SMTP relay; needs
  `BREVO_SMTP_LOGIN` (Brevo account email) set to actually send.

Domain `debanshupaul.me`; sender `outreach@debanshupaul.me`. **Do real sends only
to controlled test inboxes** — real prospects are live executives; don't blast.
Keys live in `backend/.env` (gitignored) — never commit or store them in memory.
Run mock mode (`--mock`) for zero-credit demos; Ocean/Prospeo/enrich each cost credits.

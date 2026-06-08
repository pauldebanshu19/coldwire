# Coldwire — Automated Cold-Outreach Pipeline

**One company domain in → lookalike companies → decision-makers → verified work
emails → personalized outreach sent.** Zero humans in the loop except a single
approval gate before any mail fires.

```
stripe.com ─▶ Ocean.io ─▶ Prospeo ─▶ Prospeo ─▶ [approve] ─▶ Brevo
              lookalike   C-suite /   reveal      safety       send
              companies   VP + URLs   work email  checkpoint   outreach
```

You type a single seed company. Coldwire expands it into similar companies,
surfaces their decision-makers, resolves verified work emails, shows you a
summary with a rendered sample, and — only after you approve — sends
personalized outreach. Everything between the input and the gate is automatic.

---

## Repo layout

```
coldwire/
├── backend/     Python — the pipeline engine, CLI, FastAPI API, Celery workers
├── frontend/    Next.js 16 — landing, auth, live job view, approval gate, results
├── PRD.md       full product/architecture spec
├── script.md    demo-video script (scene-by-scene voiceover)
└── README.md    this file
```

The pipeline is a **pure-Python engine** with no web/queue imports. The CLI calls
it directly; the API and the background workers call the exact same functions.
The engine is built once and reused everywhere.

---

## Quick start

**Backend (zero infra — SQLite + in-process tasks):**
```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in provider keys + Supabase
MOCK=true python main.py        # http://localhost:8000  (Swagger at /docs)
```

**Frontend:**
```bash
cd frontend
bun install                     # or pnpm / npm
bun run dev                     # http://localhost:3000
```

**CLI (the take-home's core, no server):**
```bash
cd backend && . .venv/bin/activate
python cli.py stripe.com --mock     # fake providers, zero credits, full flow + y/N gate
```

`MOCK=true` everywhere = fake providers, **zero credits, no real email** — the
fastest way to see the whole pipeline run.

---

## Architecture

```
        ┌──────────────────────────────┐
        │     Next.js 16 frontend      │  landing · auth · live job view
        │  submit · SSE progress ·     │  approval gate · results · history
        │  approval gate · results     │
        └───────────────┬──────────────┘
                        │ REST + SSE   (Supabase access token as bearer)
        ┌───────────────▼──────────────┐
        │      FastAPI API (stateless) │  /api/jobs · /events · /review
        │                              │  /approve · /cancel · /results
        └──────┬──────────────┬────────┘
   enqueue job │              │ status / approve
               ▼              ▼
        ┌────────────┐  ┌───────────────┐
        │   Redis    │  │  PostgreSQL   │  jobs · companies · contacts
        │ queue ·    │  │  (durable)    │  emails · outreach · users
        │ cache ·    │  └───────────────┘
        │ rate-limit │
        │ · events   │
        └─────┬──────┘
   pull tasks │
              ▼
        ┌───────────────────────────────┐
        │      Celery worker pool        │  runs Stage 1→2→3→[gate]→4
        │   uses the pure pipeline core  │  via the same engine
        └──────────────┬────────────────┘
                       │ rate-limited HTTP (httpx) + retries + circuit breakers
          ┌────────────┼────────────┬─────────────┐
          ▼            ▼            ▼             ▼
       Ocean.io     Prospeo      Prospeo        Brevo
       lookalikes   prospect     resolve        send
```

**Zero-infra mode:** with no `DATABASE_URL`/`REDIS_URL`, the API falls back to
SQLite + in-process asyncio tasks + an in-memory event bus — runs on one machine
with no Postgres/Redis. Set those env vars and the **same code** switches to
Postgres + Celery + Redis Streams.

---

## What's built

**The pipeline (four integrations, real APIs)**
- **Ocean.io** — seed domain → lookalike companies (cursor pagination, credit-aware).
- **Prospeo** — company → C-suite/VP decision-makers + LinkedIn (seniority-filtered, paginated).
- **Prospeo enrich** — LinkedIn → revealed verified work email (search returns *masked* previews; enrich reveals them). *(This is the "resolve" stage — Eazyreach was dropped in favour of Prospeo for both prospect and resolve.)*
- **Brevo** — personalized outreach send (REST `api-key` or SMTP relay; DKIM-signed from your domain).

**The approval gate** — a hard stop with its own job status. The summary shows
companies / contacts / deliverable / skipped **and a rendered sample email**.
Nothing sends until you approve; crash-safe (a worker restart never auto-sends).

**Resilience & production concerns**
- Per-provider **rate limiting** (token bucket; Redis-backed + global across workers when `REDIS_URL` is set).
- **Retries** with exponential backoff + jitter, honoring `429` / `Retry-After`; retryable vs terminal errors distinguished (never retry an auth failure into a ban).
- **Circuit breakers** per provider — a failing provider pauses just its stage instead of crashing the run.
- **Caching** of every paid call, keyed on input (Redis or on-disk) → repeated work is free.
- **De-duplication** — companies by domain, contacts by LinkedIn URL, people by resolved email before send (never mail the same human twice).
- **Idempotency** — job submission key + `outreach.idempotency_key` → a retry can't double-send.
- **Partial-failure tolerance** — a company with no contacts, an unresolvable email, or one send failure is recorded and skipped; the run completes with whatever it gathered.
- **Dead-letter queue** — Celery tasks that exhaust retries land in a Redis DLQ for inspection.
- **Compliance** — `List-Unsubscribe` header + unsubscribe link on every mail; emails redacted in logs; a `TEST_RECIPIENT` switch redirects all sends to one controlled inbox for safe demos.

**Auth** — Supabase (Google + email/password). The frontend signs in; the
backend verifies the access token against Supabase and scopes jobs per user.

---

## Tech stack

| Layer | Choice |
|---|---|
| Engine | Python 3.12+, Pydantic v2, httpx (async) |
| API | FastAPI (+ SSE), Supabase auth |
| Queue / workers | Celery + Redis (or in-process fallback) |
| DB | PostgreSQL via SQLAlchemy 2.0 async (SQLite fallback) |
| Cache / rate-limit / events | Redis (Streams for SSE) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind v4, shadcn UI |
| Containers | Docker + docker-compose (Postgres · Redis · API · worker) |

---

## Demo & safety

- For a credit-free run: `MOCK=true`.
- For a real run on camera: re-use a domain you've already processed (e.g.
  `stripe.com`) — its results are **cached**, so it resolves fast with no extra
  credits or rate-limit waits.
- `TEST_RECIPIENT` in `backend/.env` redirects **all** outreach to one inbox you
  control (each send still counts against the provider's daily quota).
- See [`script.md`](script.md) for a scene-by-scene demo-video script.

## More

- Backend details, CLI, API, real provider API notes → [`backend/README.md`](backend/README.md)
- Frontend screens, routes, design → [`frontend/README.md`](frontend/README.md)
- Full spec → [`PRD.md`](PRD.md)

# Conduit — Automated Cold-Outreach Pipeline (backend)

One seed domain in → lookalike companies → decision-makers → verified work
emails → personalized outreach sent. Zero humans in the loop except **one
approval gate** before any mail fires.

```
acme.com ─▶ Ocean.io ─▶ Prospeo ─▶ Eazyreach* ─▶ [approve] ─▶ Brevo
            lookalikes  C-suite/VP  reveal email   y/N gate    send
```
\* No Eazyreach key yet → Stage 3 falls back to Prospeo `enrich-person`, which
reveals the same verified email. Drop in the Eazyreach key later with no code
change.

This is **Phase 1**: the gradeable core (`core/`) + a live-demo CLI (`cli.py`).
The core is pure Python with no web/queue imports, so the upcoming FastAPI +
Celery layers (Phases 2–5 in `PRD.md`) call the exact same engine.

---

## Quick start

```bash
cd backend
uv venv .venv && . .venv/bin/activate      # or: python -m venv .venv
uv pip install -r requirements.txt          # or: pip install -r requirements.txt
cp .env.example .env                        # then fill in keys (a .env is already present)

# Safe, zero-credit end-to-end run (fake providers):
python cli.py acme.com --mock

# Real run, stop at the approval gate (no email sent):
python cli.py stripe.com --dry-run --max-companies 3 --max-contacts 2

# Real run with the y/N prompt before sending:
python cli.py stripe.com
```

### CLI flags
| Flag | Meaning |
|---|---|
| `--mock` | fake providers, **zero credits**, no real email |
| `--dry-run` | run Stages 1–3, render the summary, stop at the gate |
| `--yes` | auto-approve the gate (non-interactive — use with care) |
| `--max-companies N` / `--max-contacts N` | cap the fan-out (saves credits) |
| `--out results.csv` | export per-contact send status |
| `--log-level DEBUG` | verbose logging |

---

## Run the backend (web API)

`backend/main.py` exposes the FastAPI `app`.

```bash
cd backend
source ~/python/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Prepend `MOCK=true` for a zero-credit demo (fake providers, no real email):
```bash
MOCK=true python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Alternative entrypoint with the same result: `python main.py` (`--port`, `--reload` flags).

No Postgres/Redis required — defaults to SQLite + in-process tasks.

**Check it's running:**
- `curl localhost:8000/health` → `{"status":"ok","queue":"in-process"}`
- Open **http://localhost:8000/docs** (Swagger UI) to click-test every endpoint.

**Stop it:** `Ctrl+C` (or `pkill -f main.py`).

For the full Postgres + Redis + Celery stack, see [Phase 2](#phase-2--web-product-fastapi--postgres--celeryredis) below (`docker compose up --build`).

---

## Tests

```bash
python -m pytest -q
```
Covers domain normalization, dedup keys, HTTP retry/backoff classification
(429 retried, 401 terminal, exhaustion), the end-to-end pipeline in mock mode,
the approval gate (sends only when approved), cross-company email dedup, and
partial-failure tolerance (one bad company doesn't sink the run).

---

## Architecture

```
core/
├── models.py        Company, Contact, Email, SendResult, Review (Pydantic v2)
├── config.py        env/.env settings (pydantic-settings)
├── errors.py        Retryable vs Terminal vs Auth — drives retry decisions
├── http.py          shared transport: cache → rate-limit → retry/backoff → classify
├── ratelimit.py     per-provider token bucket (Redis-ready interface)
├── cache.py         TTL'd result cache (paid-call dedup; Redis-ready interface)
├── clients/         one client per provider (auth + pagination + parse)
│   ├── ocean.py     Stage 1   POST /v3/search/companies   (x-api-token)
│   ├── prospeo.py   Stage 2   POST /search-person          (X-KEY) + enrich-person
│   ├── eazyreach.py Stage 3   LinkedIn → email             (key pending)
│   ├── brevo.py     Stage 4   REST or SMTP send            (api-key / SMTP relay)
│   └── mock.py      deterministic fake providers
├── stages/          source · prospect · resolve · send  (one stage = one unit)
├── outreach.py      personalized email copy (text + HTML + unsubscribe)
└── pipeline.py      orchestrates 1→2→3→[gate]→4, emits progress events
cli.py               live-demo entrypoint over core.pipeline
```

Each stage is independently testable with mocked HTTP and swappable — "tweak a
stage on the spot" is a one-file change.

### Resilience & production concerns (already wired in Phase 1)
- **Retries/backoff** — every external call: exponential backoff + jitter, honours `Retry-After`, caps attempts. Retryable (429/5xx/timeout) vs terminal (401/400/403) are distinguished so an auth failure never retries into a ban.
- **Rate limiting** — per-provider token bucket; a worker acquires a token before each call. Prospeo's limit is strict, so its bucket is conservative and 429s are absorbed by retry.
- **Caching** — every paid call keyed on its input (`ocean:lookalikes:{seed}`, `prospeo:search:{domain}:p{n}`, `prospeo:enrich:{url}`). Re-runs and repeated people cost credits once.
- **De-duplication** — companies by domain, contacts by LinkedIn URL, and people by resolved email before send (never mail the same human twice).
- **Partial-failure tolerance** — a company with no contacts, an unresolvable email, or a single send error is recorded and skipped; the run completes with whatever it gathered.
- **Approval gate** — its own job state; nothing sends without an explicit yes. Omitting the approver defaults to *cancel*.
- **Compliance** — `List-Unsubscribe` header + visible unsubscribe link on every mail; emails are redacted (`d***@acme.com`) in logs.

---

## Real API notes (confirmed against the live APIs)

**Ocean.io** — `POST https://api.ocean.io/v3/search/companies`, header `x-api-token`.
Body: `{"size": N, "searchAfter": <cursor|null>, "companiesFilters": {"lookalikeDomains": ["seed.com"]}}`.
Response: `{"searchAfter", "total", "creditsUsed", "companies": [{"company": {"domain", "companySize", "industries", "primaryCountry", ...}}]}`.
Pagination is cursor-based (`searchAfter`). **Each search spends credits**, so `size` is capped at the requested count and results are cached.

**Prospeo** — header `X-KEY`.
- Search: `POST /search-person`, body `{"page", "filters": {"company": {"websites": {"include": ["acme.com"]}}, "person_seniority": {"include": ["Founder/Owner","C-Suite","Partner","Vice President","Head"]}}}`. Response `{"results": [{"person": {...}, "company": {...}}], "pagination": {"total_page", ...}}`. The person's current title/seniority/department live in `job_history[ current=true ]`.
- **Emails in search are masked** (`{"email": "d****@acme.com", "revealed": false}`) — not sendable.
- Reveal: `POST /enrich-person`, body `{"data": {"linkedin_url": "..."}}` → `person.email = {"email", "status", "revealed": true, "verification_method"}`. This is the Stage-3 reveal (a paid call).

**Eazyreach** — API docs are behind the dashboard; endpoint/auth are isolated in `clients/eazyreach.py` (one-spot change) and the resolver parser is defensive. Until a key is set, Stage 3 uses Prospeo `enrich-person`.

**Brevo** — Stage 4 supports two transports (`BREVO_TRANSPORT=auto` picks by key type):
- `rest` — `POST https://api.brevo.com/v3/smtp/email`, header `api-key`. **Needs an API v3 key (`xkeysib-…`).**
- `smtp` — Brevo SMTP relay via `aiosmtplib`. **Works with the SMTP key you have (`xsmtpsib-…`).** Set `BREVO_SMTP_LOGIN` to your Brevo account login email.

---

## Sending for real (Stage 4) — do this safely

The provided Brevo key is an **SMTP key** (`xsmtpsib-…`), so `auto` selects the
SMTP transport. To actually send:

1. In `.env`, set `BREVO_SMTP_LOGIN=<your Brevo account login email>`.
2. Verify a sender on your domain in Brevo (e.g. `outreach@debanshupaul.me`) —
   add SPF/DKIM for `debanshupaul.me` so mail isn't junked.
3. **Test against an address you control**, not the real prospects:
   ```bash
   python cli.py stripe.com --max-companies 1 --max-contacts 1
   ```
   Review the summary, type `y` only when the sample looks right.

A brand-new domain with no warm-up will land in spam on a real blast — for the
interview demo, send to one or two controlled inboxes. (Or get an API v3 key
`xkeysib-…` and set `BREVO_TRANSPORT=rest` for the cleaner REST path with
message IDs.)

---

## Phase 2 — web product (FastAPI + Postgres + Celery/Redis)

Same engine, now durable and queue-driven. Submit returns instantly with a
`job_id`; a worker runs Stages 1–3, stops at the gate; the frontend streams
progress over SSE; approval enqueues Stage 4.

### Run it two ways

**Zero-infra local** (SQLite + in-process tasks + in-memory event bus — no
Postgres/Redis needed):
```bash
. .venv/bin/activate
MOCK=true python main.py            # http://localhost:8000  (docs at /docs)
```

**Production stack** (Postgres + Redis + API + autoscalable Celery workers):
```bash
docker compose up --build            # add MOCK=true to demo without credits
# API on :8000, worker consumes the queue, Postgres + Redis backing
```
The switch is automatic: set `REDIS_URL` → Celery + Redis Streams; unset →
in-process. Same code path.

### API (PRD §8)
```
POST /api/auth/register | /api/auth/login        -> { access_token }   (JWT bearer)
POST /api/jobs            { seed_domain }         -> 202 { job_id }     (Idempotency-Key header)
GET  /api/jobs                                    list caller's jobs
GET  /api/jobs/{id}                               -> { status, stats, error }
GET  /api/jobs/{id}/events?token=JWT              SSE stage-progress stream
GET  /api/jobs/{id}/review                        -> summary + sample email (the gate)
POST /api/jobs/{id}/approve                       fire Stage 4
POST /api/jobs/{id}/cancel                        abort before send (0 emails)
GET  /api/jobs/{id}/results                       -> per-contact sent/failed/skipped
```

### Phase-2 layer
```
app_settings.py     infra settings (DB/Redis/JWT) — kept out of the pure engine
db/models.py        users · jobs · companies · contacts · emails · outreach (PRD §4)
db/session.py       async SQLAlchemy 2.0 (asyncpg / aiosqlite), NullPool
api/                main · routes_auth · routes_jobs · deps · security(JWT+bcrypt)
api/service.py      persists each stage; splits the pipeline across the gate
api/events.py       event bus: MemoryBus | RedisStreamBus + SSE
api/dispatch.py     Celery .delay  ↔  in-process asyncio task
workers/            celery_app · tasks (asyncio.run around the async service)
docker-compose.yml  db · redis · api · worker     Dockerfile · .env(.example)
```
Tests (`tests/test_api.py`): full lifecycle (register → submit → gate → approve →
COMPLETED), cancel blocks send, idempotent submit, auth required, no double-send.
Validated live on the Docker stack: Celery worker processed the job cross-process,
SSE streamed via Redis Streams, 15 `SENT` rows landed in Postgres.

**Job lifecycle:** `QUEUED → SOURCING → PROSPECTING → RESOLVING →
AWAITING_APPROVAL → SENDING → COMPLETED` (or `CANCELLED` / `FAILED`). The gate is
its own status, so a worker restart mid-job never auto-sends. Idempotency:
`(user, Idempotency-Key)` dedups submits; `outreach.idempotency_key =
job:contact` makes a retried send a no-op.

Production note: `AUTO_CREATE_TABLES=true` bootstraps the schema via
`create_all` for the demo; swap in Alembic migrations for real deploys.

---

## What's done vs next

**Phase 1 (engine + CLI):** all four integrations, approval gate,
retries/rate-limit/cache/dedup/partial-failure, mock mode. Validated live:
`stripe.com → razorpay/cashfree → real decision-makers → revealed emails → gate`.

**Phase 2 (web product):** FastAPI + Postgres + Celery/Redis, JWT auth, SSE
progress, durable job state, idempotency, one-command docker-compose. ✅

**Next (per `PRD.md`):** Next.js frontend (Phase 3), global Redis
rate-limit/circuit-breakers/DLQ + per-tenant fairness (Phase 4), autoscaling +
load test against mocked providers (Phase 5).

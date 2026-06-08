# Coldwire — backend

The pipeline engine, a live-demo CLI, the FastAPI API, and the Celery workers.

```
stripe.com ─▶ Ocean.io ─▶ Prospeo ─▶ Prospeo ─▶ [approve] ─▶ Brevo
              lookalike   C-suite/    reveal      gate         send
              companies   VP + URLs   work email
```

The **engine** (`core/`) is pure Python — no FastAPI/Celery/DB imports. The CLI,
the API, and the background workers all call the exact same stage functions, so
the pipeline is written once.

> Email resolution (stage 3) runs on **Prospeo `enrich-person`**. Prospeo's
> search returns *masked* email previews; enrich reveals the real verified
> address. (An Eazyreach client used to sit here; it was removed in favour of
> Prospeo for both prospect and resolve.)

---

## Run the API

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # fill provider keys + Supabase (a .env may already exist)

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
# or:  python main.py    (--port / --reload flags)
```

Prepend `MOCK=true` for a zero-credit run (fake providers, no real email).
No Postgres/Redis required — it defaults to **SQLite + in-process tasks**.

**Check it:** `curl localhost:8000/health` → `{"status":"ok","queue":"in-process"}`
· open **http://localhost:8000/docs** (Swagger).

### Production stack (Postgres + Redis + Celery)
```bash
docker compose up --build            # API :8000 · worker · Postgres · Redis
```
The switch is automatic: set `DATABASE_URL` + `REDIS_URL` → Celery + Redis
Streams + Redis-global rate-limit/cache. Unset → in-process. Same code path.

---

## The CLI (the gradeable core, no server)

```bash
python cli.py stripe.com --mock        # fake providers, zero credits, full flow + y/N gate
python cli.py stripe.com --dry-run     # real APIs, stop at the gate (no send)
python cli.py stripe.com               # real run with the Proceed? [y/N] prompt
```

| Flag | Meaning |
|---|---|
| `--mock` | fake providers, **zero credits**, no real email |
| `--dry-run` | run stages 1–3, render the summary, stop at the gate |
| `--yes` | auto-approve the gate (non-interactive) |
| `--max-companies N` / `--max-contacts N` | cap the fan-out (saves credits) |
| `--out results.csv` | export per-contact send status |

---

## The engine (`core/`)

```
core/
├── models.py        Company · Contact · Email · SendResult · Review (Pydantic v2)
├── config.py        engine settings from env/.env (provider keys, limits, redis_url)
├── errors.py        Retryable vs Terminal vs Auth — drives retry/breaker decisions
├── http.py          shared transport: cache → rate-limit → breaker → retry/backoff → classify
├── ratelimit.py     per-provider token bucket (in-memory + Redis-global)
├── breaker.py       per-provider circuit breakers
├── cache.py         result cache (on-disk + Redis), TTL'd, paid-call dedup
├── clients/         one client per provider — auth + pagination + parse
│   ├── ocean.py     POST /v3/search/companies      (x-api-token)
│   ├── prospeo.py   POST /search-person + enrich-person  (X-KEY)
│   ├── brevo.py     POST /v3/smtp/email or SMTP relay     (api-key / SMTP)
│   └── mock.py      deterministic fake providers (--mock)
├── stages/          source · prospect · resolve · send   (one stage = one unit)
├── outreach.py      personalized email copy (text + HTML + unsubscribe)
└── pipeline.py      orchestrates 1→2→3→[gate]→4, emits progress events
```

Each stage is independently testable with mocked HTTP and swappable — "tweak a
stage on the spot" is a one-file change.

### Resilience & production concerns
- **Retries/backoff** — exponential backoff + jitter, honours `Retry-After`; retryable (429/5xx/timeout) vs terminal (401/400/403) distinguished so an auth failure never retries into a ban.
- **Rate limiting** — token bucket per provider. With `REDIS_URL` set it's an atomic Redis token bucket → **global across all worker processes**, not per-process.
- **Circuit breakers** — per provider; after repeated failures the breaker opens and that stage fast-fails (`CircuitOpenError`) for a cooldown, then half-opens to probe recovery. One dead provider never crashes the run.
- **Caching** — every paid call keyed on its input (`ocean:lookalikes:{seed}`, `prospeo:search:{domain}:p{n}`, `prospeo:enrich:{url}`). Redis when configured, else on-disk. Re-runs and repeated people cost credits once.
- **De-duplication** — companies by domain, contacts by LinkedIn URL, people by resolved email before send.
- **Partial-failure tolerance** — missing contacts / unresolvable emails / single send errors are recorded and skipped; the run completes with whatever it gathered.
- **Compliance** — `List-Unsubscribe` header + visible unsubscribe link; emails redacted (`d***@acme.com`) in logs. `TEST_RECIPIENT` redirects all sends to one inbox for safe demos.

---

## The web layer

```
app_settings.py     infra settings (DB / Redis / Supabase / CORS) — kept out of the pure engine
db/models.py        users · jobs · companies · contacts · emails · outreach
db/session.py       async SQLAlchemy 2.0 (asyncpg / aiosqlite), NullPool
api/
  main.py           FastAPI app (CORS, lifespan, health)
  routes_jobs.py    jobs / events(SSE) / review / approve / cancel / results / delete
  deps.py           DB session + current user (from Supabase token)
  supabase_auth.py  verifies the access token against {SUPABASE_URL}/auth/v1/user (cached)
  service.py        persists each stage; splits the pipeline across the gate
  events.py         event bus: MemoryBus | RedisStreamBus + SSE formatting
  dispatch.py       Celery .delay  ↔  in-process asyncio task
workers/
  celery_app.py     Celery config (eager when no Redis)
  tasks.py          run_job / run_send (asyncio.run around the async service) + Redis DLQ
docker-compose.yml  db · redis · api · worker        Dockerfile · .env(.example)
```

### API
```
Auth: Supabase. Sign in on the frontend; send the access token as
      Authorization: Bearer <token>. The backend verifies it and upserts the user.

POST   /api/jobs            { seed_domain }    -> 202 { job_id }   (Idempotency-Key header)
GET    /api/jobs                               list caller's jobs
GET    /api/jobs/{id}                          -> { status, stats, error }
GET    /api/jobs/{id}/events?token=...         SSE stage-progress stream
GET    /api/jobs/{id}/review                   -> summary + sample email (the gate)
POST   /api/jobs/{id}/approve                  fire the send stage
POST   /api/jobs/{id}/cancel                   abort before send (0 emails)
GET    /api/jobs/{id}/results                  -> per-contact sent/failed/skipped
DELETE /api/jobs/{id}                          delete a run + all its rows
```

### Job lifecycle
```
QUEUED → SOURCING → PROSPECTING → RESOLVING → AWAITING_APPROVAL → SENDING → COMPLETED
                                                      └── CANCELLED        └── FAILED
```
The gate (`AWAITING_APPROVAL`) is its own status, so a worker restart mid-job
never auto-sends. **Idempotency:** `(user, Idempotency-Key)` dedups submits;
`outreach.idempotency_key = job:contact` makes a retried send a no-op.

**Dead-letter queue:** a Celery task that exhausts retries or crashes is recorded
to a Redis list `coldwire:dlq`. (Business-level failures are already durable as
`FAILED` jobs in Postgres.)

Schema bootstrap uses `create_all` (`AUTO_CREATE_TABLES=true`); swap in Alembic
for real migrations.

---

## Real API notes (confirmed against the live APIs)

**Ocean.io** — `POST https://api.ocean.io/v3/search/companies`, header `x-api-token`.
Body `{"size": N, "searchAfter": <cursor|null>, "companiesFilters": {"lookalikeDomains": ["seed.com"]}}`.
Response `{"searchAfter", "total", "creditsUsed", "companies": [{"company": {"domain", "companySize", "industries", ...}}]}`.
Cursor pagination via `searchAfter`. **Each search spends credits**, so `size` is capped and results cached.

**Prospeo** — header `X-KEY`.
- Search: `POST /search-person`, body `{"page", "filters": {"company": {"websites": {"include": ["acme.com"]}}, "person_seniority": {"include": ["Founder/Owner","C-Suite","Partner","Vice President","Head"]}}}`. Response `{"results": [{"person", "company"}], "pagination": {"total_page", ...}}`. Current title/seniority/department live in `person.job_history[ current=true ]`.
- **Emails in search are masked** (`{"email": "d****@acme.com", "revealed": false}`) — not sendable.
- Reveal: `POST /enrich-person`, body `{"data": {"linkedin_url": "..."}}` → `person.email = {"email","status","revealed": true,"verification_method"}` (a paid call — `INSUFFICIENT_CREDITS` if the account runs out).

**Brevo** — `BREVO_TRANSPORT=auto` picks by key type:
- `rest` — `POST https://api.brevo.com/v3/smtp/email`, header `api-key` (needs an API v3 key `xkeysib-…`).
- `smtp` — Brevo SMTP relay via `aiosmtplib` (works with an SMTP key `xsmtpsib-…`; set `BREVO_SMTP_LOGIN`).
- Brevo enforces **Authorised IPs** — add your IP (or disable) in Brevo → Security, else sends 401.

---

## Sending safely
1. Verify a sender / authenticate your domain (SPF/DKIM/DMARC) in Brevo so mail isn't junked.
2. Set `TEST_RECIPIENT=you@inbox.com` in `.env` → **all** outreach redirects to that one inbox (subject tagged with the real intended recipient). Clear it to mail real prospects.
3. Keep the fan-out small (`MAX_COMPANIES` × `MAX_CONTACTS_PER_COMPANY`) — each enrich + send costs credits/quota.

---

## Tests
```bash
python -m pytest -q
```
Covers: domain normalization & dedup keys · HTTP retry/backoff classification
(429 retried, 401 terminal, exhaustion) · circuit-breaker open/half-open/recovery ·
the end-to-end pipeline in mock mode · the approval gate (sends only when approved) ·
cross-company email dedup · partial-failure tolerance · the full API lifecycle
(submit → gate → approve → COMPLETED, cancel, idempotent submit, delete, auth-required, no double-send).

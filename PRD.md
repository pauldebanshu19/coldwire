# PRD — Automated Cold-Outreach Pipeline

> Codename: **Conduit** (placeholder — rename freely)
> One seed domain in → lookalike companies → decision-makers → verified work emails → personalized outreach sent. Zero humans in the loop except a single approval gate before mail fires.

---

## 0. Read this first

The take-home asks for **one CLI program that runs four API stages end to end**. That CLI is the *gradeable core* and must exist on its own. This PRD intentionally goes further: it wraps that same core in a production web product (FastAPI backend + Next.js frontend) because the assignment says the build is yours to keep for your portfolio.

The trick that makes both possible without duplicate work: **the pipeline is a pure-Python engine with no web dependencies.** The CLI calls it directly. The web workers call the exact same functions. You build the engine once.

**Honest scaling note.** "1M user requests" here does **not** mean a million live calls to Ocean.io / Prospeo / Eazyreach / Brevo — those are credit-gated and rate-limited, so the external APIs are the hard ceiling on real throughput. "Scale" in this system means: *accept* a million job submissions without dropping or blocking, then *drain* them as fast as the external APIs + your credit budget allow, fairly across users, with caching so repeated work is free. The architecture below is built around that constraint, not around pretending the bottleneck doesn't exist. Stating this in the interview is itself the "good judgment" they grade.

---

## 1. Problem & goals

**Problem.** Sales teams manually source lookalike companies, hunt decision-makers, find emails, and write outreach. Each step is a different tool and a copy-paste handoff. We automate the entire chain behind one input.

**Primary goal.** A human types `company.domain`. The system autonomously produces a vetted list of decision-makers with verified emails, shows a summary for approval, and sends personalized outreach — no manual step between stages.

**Success criteria (mirrors the grading rubric).**
1. Runs end to end from a single input, zero manual handoffs between stages.
2. Each integration handles auth, pagination, rate limits, and errors correctly against the real API.
3. Code is modular — one stage is one independently testable, swappable unit.
4. Resilient — missing contacts, 429s, and partial failures degrade gracefully, never crash the run.
5. A safety checkpoint shows a summary before any email is sent.
6. (Bonus) Outreach copy is personalized and worth opening.

**Non-goals.**
- Not a CRM, not an email warm-up/deliverability suite, not an analytics dashboard product.
- Not real-time (sub-second) — runs are minutes-long async jobs by nature.
- Not bypassing any provider's terms or rate limits.

---

## 2. The pipeline (the core of everything)

```
INPUT: one seed domain (a company you know is a good customer)
   │
   ▼
[Stage 1] Ocean.io      seed domain ──► list of lookalike company domains
   │                                    (similar firmographics / size / market)
   ▼
[Stage 2] Prospeo       each domain ──► decision-makers (C-suite / VP) + LinkedIn URLs
   │
   ▼
[Stage 3] Eazyreach     each LinkedIn URL ──► verified, deliverable work email
   │
   ▼
[CHECKPOINT]            summary shown → human approves → only then continue
   │
   ▼
[Stage 4] Brevo         each contact ──► personalized outreach email sent
```

Every stage's output is the next stage's input. Half the build is reading each provider's API docs (auth scheme, endpoints, request/response shapes, pagination, rate limits) — treat that as a first-class task, not an afterthought.

**Stage contracts (the engine's public interface):**

| Stage | Function (conceptual) | Input | Output |
|---|---|---|---|
| 1 Ocean | `find_lookalikes(seed_domain)` | `str` | `list[Company]` |
| 2 Prospeo | `find_contacts(domain)` | `str` | `list[Contact]` |
| 3 Eazyreach | `resolve_email(linkedin_url)` | `str` | `Email \| None` |
| 4 Brevo | `send_outreach(contact, body)` | `Contact, str` | `SendResult` |

Each is pure I/O against one provider, fully unit-testable with mocked HTTP, and swappable (so "tweak a stage on the spot" in the interview is trivial).

---

## 3. System architecture

```
                          ┌─────────────────────────────┐
                          │      Next.js 14 frontend     │
                          │  submit · live progress ·    │
                          │  approval gate · results     │
                          └───────────┬─────────────────┘
                                      │ REST + SSE
                          ┌───────────▼─────────────────┐
                          │     FastAPI API (stateless)  │   ◄── horizontally scaled
                          │  /jobs  /approve  /events    │       behind a load balancer
                          └─────┬───────────────┬────────┘
                  enqueue job   │               │  read status / write approval
                                ▼               ▼
                       ┌────────────────┐  ┌──────────────────┐
                       │  Redis (queue, │  │   PostgreSQL      │
                       │  cache, rate-  │  │  jobs, companies, │
                       │  limit buckets)│  │  contacts, emails,│
                       └───────┬────────┘  │  outreach         │
                               │           └──────────────────┘
                  pull tasks   │
                               ▼
                       ┌────────────────────────────┐
                       │   Celery worker pool        │  ◄── autoscaled on queue depth
                       │  runs Stage 1→2→3→(gate)→4  │
                       │  uses the pure pipeline core│
                       └──────────┬─────────────────┘
                                  │ rate-limited HTTP (httpx + tenacity)
            ┌──────────┬──────────┼───────────┬──────────────┐
            ▼          ▼          ▼           ▼              ▼
        Ocean.io   Prospeo    Eazyreach     Brevo      (per-provider
                                                        circuit breakers)
```

**Why async + queue (not synchronous HTTP).** A single run fans out: Ocean returns *N* companies → each triggers paginated Prospeo calls → each contact triggers an Eazyreach resolution → approved contacts trigger Brevo sends. This is minutes long, I/O-bound, rate-limited, and partial-failure-prone. An HTTP request can't hold that open. So: **submit returns instantly with a `job_id`; workers do the work; the frontend streams progress.**

**Components**

- **Pipeline core (`core/`)** — pure Python, no FastAPI/Celery imports. The four stage modules + models + provider HTTP clients. This is what the CLI and the workers both call.
- **CLI (`cli.py`)** — thin wrapper over the core for the live demo. Prints stage-by-stage progress to the terminal, hits the same checkpoint (a `y/N` prompt before sending).
- **API (FastAPI)** — stateless. Accepts jobs, returns status, streams progress via SSE, exposes the approval endpoint. No business logic beyond orchestration glue.
- **Queue + workers (Celery + Redis)** — decouples submission from execution; absorbs bursts; provides retries, backoff, and a dead-letter path.
- **PostgreSQL** — durable state for jobs and every entity discovered.
- **Redis** — three jobs: broker for the queue, cache for paid API results, and shared token-bucket store for global rate limiting across all workers.

---

## 4. Data model

```
users(id, email, password_hash, created_at)

jobs(
  id, user_id FK, seed_domain, status, 
  created_at, approved_at, completed_at,
  error, stats_jsonb            -- counts cached for fast status reads
)
  status ∈ { QUEUED, SOURCING, PROSPECTING, RESOLVING,
             AWAITING_APPROVAL, SENDING, COMPLETED, FAILED, CANCELLED }

companies(
  id, job_id FK, domain, name, size, industry, raw_jsonb,
  UNIQUE(job_id, domain)        -- dedup lookalikes within a job
)

contacts(
  id, company_id FK, full_name, title, seniority, linkedin_url,
  UNIQUE(company_id, linkedin_url)
)

emails(
  id, contact_id FK, address, verification_status, deliverable bool,
  resolved_at
)

outreach(
  id, contact_id FK, brevo_message_id, status, sent_at,
  idempotency_key,
  UNIQUE(idempotency_key)       -- guarantees one send per contact per job
)
```

`stats_jsonb` on the job (e.g. `{companies: 12, contacts: 41, deliverable: 33}`) lets the status endpoint answer without joining/counting — important when a million clients poll.

---

## 5. Job lifecycle & the approval gate

```
QUEUED
  → SOURCING        Stage 1 runs, companies inserted
  → PROSPECTING     Stage 2 fans out per company, contacts inserted (deduped)
  → RESOLVING       Stage 3 resolves emails, marks deliverable / skipped
  → AWAITING_APPROVAL   ← HARD STOP. Nothing is sent yet.
        │
        │  frontend shows summary:
        │   • N companies, M contacts, K deliverable emails
        │   • the exact email template + a rendered sample for one real contact
        │   • count that will be skipped (no email / undeliverable)
        │
        ├── user clicks Approve  →  SENDING → COMPLETED
        └── user clicks Cancel   →  CANCELLED  (zero emails sent)
```

The gate is non-optional and is its own status so the system is crash-safe across it: a worker restart mid-job never auto-sends. In the **CLI**, the same gate is a printed summary + `Proceed? [y/N]` prompt.

---

## 6. Production concerns (where the grade is actually won)

**Rate limiting.** Token-bucket per provider stored in Redis so the limit is *global* across all workers, not per-process. A worker must acquire a token before any external call. Respect `429` + `Retry-After` — read it, sleep, retry, don't hammer.

**Retries & backoff.** Wrap every external call with `tenacity`: exponential backoff + jitter, capped attempts. Distinguish retryable (`429`, `5xx`, timeouts) from terminal (`401`, `400`) — never retry an auth failure into a ban.

**Circuit breakers.** Per provider. If Eazyreach starts failing consistently, open the breaker, pause that stage, keep the rest of the job's data intact, and resume when it recovers. One dead provider must not torch the whole run.

**Caching (this is also cost control).** Every paid call is cached in Redis keyed on its input: `ocean:lookalikes:{seed}`, `eazyreach:{linkedin_url}`. Two users seeding the same domain, or the same person appearing at multiple companies, costs credits once. Set sane TTLs (firmographics drift; emails go stale).

**De-duplication** (they *will* ask this in the interview):
- Companies: unique on `(job_id, domain)`.
- Contacts: unique on `(company_id, linkedin_url)`.
- People across companies: dedupe on resolved email before sending — never mail the same human twice in one job.

**Idempotency.**
- Job submission accepts an idempotency key so a double-clicked "Submit" creates one job.
- Brevo send keyed on `(job_id, contact_id)` via the `outreach.idempotency_key` unique constraint — a worker retry after a network blip cannot double-send.

**Partial-failure tolerance.** A company with no decision-makers yields zero contacts and moves on. A contact whose email won't resolve is recorded as skipped, excluded from the send count, and surfaced in the summary. The run completes with whatever it successfully gathered.

**Dead-letter queue.** Tasks that exhaust retries land in a DLQ for inspection instead of silently vanishing or blocking the queue.

**Compliance** (a "good judgment" talking point). Cold email is legally constrained (CAN-SPAM, GDPR/PECR). Bake in: a suppression/unsubscribe list checked before send, an unsubscribe link in the template, and never logging full email bodies with PII in plaintext.

---

## 7. Scaling to high volume

The system must accept a flood of submissions gracefully and process them as fast as the external limits allow.

- **Stateless API tier** behind a load balancer, horizontally autoscaled. No session state in the process.
- **Queue as shock absorber.** Submissions are cheap DB inserts + an enqueue. The queue depth is the backpressure signal; nothing blocks the user.
- **Worker autoscaling** keyed on queue depth. More backlog → more workers, up to the ceiling the *external APIs* permit.
- **Per-tenant fair scheduling & quotas.** One user submitting 100k domains must not starve everyone else. Round-robin or weighted-fair consumption per user; hard per-user credit/job quotas.
- **PostgreSQL**: connection pooling via PgBouncer; read replicas for the high-volume status/poll reads; partition `companies`/`contacts` by `job_id` range if needed.
- **Status reads** served from `stats_jsonb` (and cacheable) so polling doesn't hammer the DB.
- **The real ceiling is external.** Effective send rate = min(your worker capacity, each provider's rate limit, your remaining credits). Caching pushes that ceiling up for free by eliminating repeat work. Design states this honestly rather than promising infinite throughput to Brevo.

**Load-test plan.** Mock the four providers with a local stub server (latency + 429 injection). Fire synthetic job submissions with `k6`/`locust`, confirm: submissions stay fast under load, queue drains at the configured rate, no double-sends, fair sharing across tenants, graceful behavior on injected 429s and provider outages.

---

## 8. API contract (FastAPI)

```
POST   /api/jobs                 { seed_domain }            → { job_id }   (idempotency-key header)
GET    /api/jobs                 list caller's jobs
GET    /api/jobs/{id}            → { status, stats, error }
GET    /api/jobs/{id}/events     SSE stream of stage progress events
GET    /api/jobs/{id}/review     → summary for the approval gate
                                   { companies, contacts, deliverable, skipped, template, sample }
POST   /api/jobs/{id}/approve    fire Stage 4
POST   /api/jobs/{id}/cancel     abort before send
GET    /api/jobs/{id}/results    → sent / failed / skipped breakdown
```

SSE event shape: `{ stage, status, count, message, ts }` — frontend renders a live timeline from these.

---

## 9. Frontend (Next.js 14, App Router)

**Screens**
1. **Submit** — single input for the seed domain, validation, submit → redirect to job view.
2. **Job / live progress** — timeline driven by the SSE stream: `Ocean ✓ 12 companies → Prospeo ⟳ 28 contacts → Eazyreach …`. Real-time, no manual refresh.
3. **Approval gate** — the summary table (companies / contacts / deliverable / skipped), the email template, and one rendered sample against a real contact. `Approve & Send` / `Cancel`.
4. **Results** — per-contact send status, failures, skipped-with-reason; CSV export.
5. **History** — list of past jobs with status.

**Stack:** TypeScript, TanStack Query for server state, native `EventSource` for SSE, Tailwind + shadcn/ui. Auth via JWT (or Supabase Auth if you want it batteries-included — fits your existing stack).

---

## 10. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Pipeline core | Python 3.12, Pydantic v2 | typed models pass cleanly between stages |
| HTTP | `httpx` (async) + `tenacity` | async I/O, retry/backoff built in |
| API | FastAPI | async-native, your existing strength |
| Queue | Celery + Redis | mature, autoscaling-friendly (RQ is a lighter alt) |
| DB | PostgreSQL (+ PgBouncer) | relational data, replicas for read scale |
| Cache / broker / rate-limit | Redis | one tool, three jobs |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | matches your prior infra choices |
| Frontend | Next.js 14, TS, TanStack Query, Tailwind, shadcn/ui | your portfolio stack |
| Containerization | Docker + docker-compose | one-command local spin-up |
| Deploy | Railway/Render/Fly or AWS ECS | LB + autoscaled workers |
| Observability | structured logging + Prometheus/Grafana, OpenTelemetry tracing | per-job timeline, API error rates, credits burned |

---

## 11. Repo structure

```
conduit/
├── core/                       # pure engine — no web/queue imports
│   ├── models.py               # Company, Contact, Email, SendResult (Pydantic)
│   ├── config.py               # keys from env / secrets
│   ├── clients/                # one HTTP client per provider: auth + pagination + retry
│   │   ├── ocean.py
│   │   ├── prospeo.py
│   │   ├── eazyreach.py
│   │   └── brevo.py
│   ├── stages/                 # one stage = one unit
│   │   ├── source.py           # Stage 1
│   │   ├── prospect.py         # Stage 2
│   │   ├── resolve.py          # Stage 3
│   │   └── send.py             # Stage 4
│   ├── ratelimit.py            # Redis token-bucket
│   ├── cache.py
│   └── pipeline.py             # orchestrates 1→2→3→gate→4
├── cli.py                      # live-demo entrypoint over core.pipeline
├── api/                        # FastAPI app
│   ├── main.py  routes.py  schemas.py  deps.py  sse.py
├── workers/
│   └── tasks.py                # Celery tasks wrapping core stages
├── db/  models.py  session.py  migrations/
├── tests/                      # mocked-HTTP unit tests per stage + e2e
├── frontend/                   # Next.js 14 app
├── docker-compose.yml
└── README.md
```

---

## 12. Build phases

**Phase 0 — Setup (do before any code).** Buy/claim ONE domain (Student Pack or Namecheap, reimbursed). Make `you@yourdomain`. Sign up Ocean.io *with that email* (it rejects personal emails — this is why the domain comes first). Then Prospeo, Eazyreach (send details for credit top-up), Brevo. Read all four API docs.

**Phase 1 — The gradeable core (highest priority).** Build `core/` + `cli.py`. One domain in → four stages fire → checkpoint prompt → emails send. This alone passes the take-home. *Get this working and explainable before anything else* — their rubric says a working slice you can explain beats a broken whole you can't.

**Phase 2 — Persist + async.** FastAPI + Postgres + Celery/Redis. Same engine, now durable and queue-driven.

**Phase 3 — Frontend.** Next.js submit → live SSE progress → approval gate → results.

**Phase 4 — Harden.** Global rate limiting, caching, retries/backoff, circuit breakers, idempotency, dedup, DLQ, structured logging + metrics.

**Phase 5 — Scale & prove it.** Autoscaling workers, per-tenant fairness, PgBouncer + replicas; load-test against mocked providers and document the numbers.

---

## 13. Risks & open questions

- **Exact API shapes are unknown until you read each doc** — auth scheme, pagination style, and rate limits differ per provider and drive the client design. Budget real time here.
- **Credit limits** cap how much you can demo live — cache aggressively and keep a tiny seed list for the demo.
- **Email deliverability/compliance** — sending from a brand-new domain with no warm-up risks spam folders; for the demo, sending to a couple of controlled addresses is safer than a real blast.
- **Cost** — every uncached Ocean/Prospeo/Eazyreach call spends credits; the cache and dedup layers are as much about money as performance.

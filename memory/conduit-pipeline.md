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

**Phase 1 (gradeable core + CLI) is DONE & validated live** (stripe.com →
razorpay/cashfree → real C-suite → revealed emails → gate). Pure engine in
`backend/core/`, demo CLI `backend/cli.py`, 16 passing tests. Next phases (FastAPI
+ Postgres + Celery, Next.js frontend, hardening, scale) not started.

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

# Conduit — frontend (Phase 3)

Next.js 16 + React 19 + Tailwind v4 + shadcn UI. The web face of the cold-outreach
pipeline: submit one domain, watch the pipeline run live, approve at the gate, see results.

## Prerequisites

The backend API must be running (see `../backend`):
```bash
cd ../backend && . .venv/bin/activate && MOCK=true python main.py   # http://localhost:8000
```

## Run

```bash
cd frontend
bun install            # or: pnpm install / npm install
bun run dev            # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` (in `.env.local`) points at the backend — defaults to
`http://localhost:8000`. Build for production: `bun run build && bun run start`.

## Screens (PRD §9)

1. **Landing / auth** (`/`) — register or sign in (JWT bearer, stored client-side).
2. **Dashboard** (`/`) — the submit console (one domain → `RUN PIPELINE`) + run history.
3. **Job / live progress** (`/jobs/[id]`) — the 4-stage pipeline lights up stage by
   stage from the **SSE** stream (`EventSource` → `/api/jobs/{id}/events`), with a live
   event feed. Status is also polled for authoritative state.
4. **Approval gate** — at `AWAITING_APPROVAL`: summary tiles (companies / contacts /
   deliverable / skipped), the rendered **sample email**, and `Approve & Send` / `Cancel`.
5. **Results** — per-contact sent / failed / skipped, with **CSV export**.

## Architecture

```
app/
  layout.tsx            fonts (IBM Plex Mono + Hanken Grotesk), dark theme, Providers
  page.tsx              landing/auth ↔ dashboard (client, auth-gated)
  jobs/[id]/page.tsx    job detail: timeline + gate + results
  globals.css           Tailwind v4 theme — "mission control" palette (lime on near-black)
lib/
  api.ts               typed backend client + token storage + types
  auth.tsx             AuthProvider / useAuth (JWT in localStorage)
  status.ts            stage + status metadata
hooks/use-job-stream.ts SSE subscription + status polling
components/
  app-header · auth-form · submit-console · job-list
  pipeline-timeline · review-gate · results-table · status-badge · providers
```

State is plain React + a small SSE/poll hook (no extra data layer). Auth is a JWT
bearer token kept in `localStorage`; the SSE endpoint takes it as a `?token=` query
param because `EventSource` can't set headers.

## Design

Dark terminal / mission-control aesthetic — signal-lime accent on near-black, IBM Plex
Mono for data + labels, grid texture and a glow that reinforces the "engine" framing.
The pipeline timeline is the centerpiece: nodes light up and count up as SSE events arrive.

# Coldwire — frontend

Next.js 16 + React 19 + Tailwind v4 + shadcn UI. The web face of the pipeline:
a marketing landing, Supabase auth, submit one domain, watch it run live, approve
at the gate, see results.

## Run

The backend API must be running first (see `../backend`):
```bash
cd ../backend && . .venv/bin/activate && MOCK=true python main.py   # http://localhost:8000
```

Then:
```bash
cd frontend
bun install            # or pnpm / npm
bun run dev            # http://localhost:3000
```

`.env.local` holds:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```
Production build: `bun run build && bun run start`.

> **Supabase:** sign-in is Google + email/password. For instant demo sign-in,
> disable email confirmation (Authentication → Providers → Email → "Confirm
> email" off). For Google OAuth, add `http://localhost:3000` to the allowed
> redirect URLs. The backend needs the same `SUPABASE_URL` + publishable key to
> verify tokens.

## Routes & screens

| Route | Screen |
|---|---|
| `/` (logged out) | **Landing** — glass navbar (Sign in → `/login`), centered hero, the four-stage pipeline, feature grid, CTA. |
| `/login` | **Auth** — Continue with Google or email/password; redirects to `/` on success. |
| `/` (logged in) | **Dashboard** — submit console (one domain → run) + run history (with delete). |
| `/jobs/[id]` | **Job view** — live 4-stage timeline from the **SSE** stream, the **approval gate** (summary tiles + rendered sample email + Approve/Cancel), and **results** (sent/failed/skipped + CSV export). |

The pipeline timeline lights up stage by stage as SSE events arrive; status is
also polled for the authoritative state. The approval gate is a hard stop —
nothing sends until you click **Approve & Send**.

## Architecture

```
app/
  layout.tsx            fonts (IBM Plex Mono + Hanken Grotesk), dark theme, Providers
  page.tsx              landing (logged out) ↔ dashboard (logged in)
  login/page.tsx        dedicated sign-in page
  jobs/[id]/page.tsx    job detail: timeline + gate + results
  globals.css           Tailwind v4 theme — "mission control" palette (lime on near-black)
lib/
  api.ts                typed backend client; pulls a fresh Supabase token per request
  auth.tsx              AuthProvider / useAuth over Supabase (Google + email)
  supabase.ts           browser Supabase client (publishable key)
  status.ts             stage + status metadata
hooks/use-job-stream.ts SSE subscription + status polling (token-gated)
components/
  app-header            glassmorphic dashboard navbar (+ sign out)
  submit-console · job-list · pipeline-timeline · review-gate · results-table
  status-badge · auth-form · providers
  landing/              Navbar · Hero · PipelineStrip · HowItRuns · Features
                        CtaSection · Reveal · content.ts · index.tsx
```

Auth is a Supabase session; the access token is sent as `Authorization: Bearer`
and refreshed automatically on each request. The SSE endpoint takes the token as
a `?token=` query param because `EventSource` can't set headers.

## Design

Dark terminal / mission-control aesthetic — signal-lime accent on near-black,
IBM Plex Mono for data + labels, a glass (frosted, blurred) navbar, grid texture
and glow. The live pipeline timeline is the centerpiece: nodes light up and count
up as events stream in.

// Typed client for the Coldwire backend (FastAPI).
// Auth is handled by Supabase; a fresh (auto-refreshed) access token is pulled
// from the Supabase client on every request so it never goes stale.

import { supabase } from "./supabase";

function normalizeBase(raw?: string): string {
  let base = (raw || "http://localhost:8000").trim().replace(/\/+$/, "");
  // tolerate a missing scheme (e.g. "host.up.railway.app") so it isn't treated
  // as a relative path and appended to the current origin.
  if (base && !/^https?:\/\//i.test(base)) base = `https://${base}`;
  return base;
}

export const API_URL = normalizeBase(process.env.NEXT_PUBLIC_API_URL);

// Cached for synchronous needs (the SSE URL); kept in sync by the AuthProvider.
let _bearer: string | null = null;
export function setBearer(token: string | null) {
  _bearer = token;
}
export function getToken(): string | null {
  return _bearer;
}

/** Current access token, refreshing it via Supabase if it's near/after expiry. */
async function freshToken(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token ?? null;
    if (token) _bearer = token;
    return token ?? _bearer;
  } catch {
    return _bearer;
  }
}

// ── Types (mirror api/schemas.py) ────────────────────────────────────
export type JobStatus =
  | "QUEUED" | "SOURCING" | "PROSPECTING" | "RESOLVING"
  | "AWAITING_APPROVAL" | "SENDING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface JobStats {
  companies?: number; contacts?: number; deliverable?: number;
  skipped?: number; sent?: number; failed?: number;
}

export interface Job {
  id: string;
  seed_domain: string;
  status: JobStatus;
  stats: JobStats;
  error?: string | null;
  created_at?: string | null;
  approved_at?: string | null;
  completed_at?: string | null;
}

export interface Review {
  job_id: string;
  status: JobStatus;
  companies: number;
  contacts: number;
  deliverable: number;
  skipped: number;
  template_subject?: string | null;
  sample_to?: string | null;
  sample_subject?: string | null;
  sample_body?: string | null;
}

export interface ResultRow {
  contact: string;
  email?: string | null;
  status: "SENT" | "FAILED" | "SKIPPED";
  message_id?: string | null;
  error?: string | null;
}
export interface Results {
  job_id: string;
  status: JobStatus;
  stats: JobStats;
  results: ResultRow[];
}

export interface SseEvent {
  stage: "ocean" | "prospeo" | "resolve" | "brevo" | "pipeline" | "heartbeat";
  status: "start" | "progress" | "done" | "skip" | "error" | "ping";
  count: number;
  message?: string;
  job_status?: JobStatus;
  ts: number;
}

// ── Core request helper ──────────────────────────────────────────────
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  const token = await freshToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
      if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join(", ");
    } catch { /* ignore */ }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Endpoints ────────────────────────────────────────────────────────
export const api = {
  createJob: (seed_domain: string, reply_to?: string) =>
    request<Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ seed_domain, reply_to: reply_to?.trim() || undefined }),
    }),
  listJobs: () => request<Job[]>("/api/jobs"),
  getJob: (id: string) => request<Job>(`/api/jobs/${id}`),
  review: (id: string) => request<Review>(`/api/jobs/${id}/review`),
  approve: (id: string, opts?: { sender_name?: string; reply_to?: string }) =>
    request<Job>(`/api/jobs/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({
        sender_name: opts?.sender_name?.trim() || undefined,
        reply_to: opts?.reply_to?.trim() || undefined,
      }),
    }),
  cancel: (id: string) => request<Job>(`/api/jobs/${id}/cancel`, { method: "POST" }),
  results: (id: string) => request<Results>(`/api/jobs/${id}/results`),
  deleteJob: (id: string) => request<void>(`/api/jobs/${id}`, { method: "DELETE" }),

  eventsUrl: (id: string) => `${API_URL}/api/jobs/${id}/events?token=${_bearer ?? ""}`,
};

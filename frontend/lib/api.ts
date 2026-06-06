// Typed client for the Conduit backend (FastAPI).

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "conduit_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
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
  stage: "ocean" | "prospeo" | "eazyreach" | "brevo" | "pipeline" | "heartbeat";
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
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Cannot reach the backend. Is it running on " + API_URL + "?", 0);
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
  register: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/register", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),

  createJob: (seed_domain: string) =>
    request<Job>("/api/jobs", { method: "POST", body: JSON.stringify({ seed_domain }) }),
  listJobs: () => request<Job[]>("/api/jobs"),
  getJob: (id: string) => request<Job>(`/api/jobs/${id}`),
  review: (id: string) => request<Review>(`/api/jobs/${id}/review`),
  approve: (id: string) => request<Job>(`/api/jobs/${id}/approve`, { method: "POST" }),
  cancel: (id: string) => request<Job>(`/api/jobs/${id}/cancel`, { method: "POST" }),
  results: (id: string) => request<Results>(`/api/jobs/${id}/results`),

  eventsUrl: (id: string) => `${API_URL}/api/jobs/${id}/events?token=${getToken() ?? ""}`,
};

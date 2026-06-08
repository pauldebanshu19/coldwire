"use client";

import { useEffect, useState } from "react";
import { api, type Job, type SseEvent } from "@/lib/api";

const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];

/**
 * Watches a job: authoritative status via polling + live progress via SSE.
 * Gated on `token` so we never call the API before the Supabase session has
 * loaded (empty bearer -> 401), and we re-subscribe when the token refreshes.
 */
export function useJobStream(id: string, token: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setJob(await api.getJob(id));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // Poll status until terminal.
  useEffect(() => {
    if (!id || !token) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      if (stopped) return;
      try {
        const j = await api.getJob(id);
        if (stopped) return;
        setJob(j);
        setError(null);
        if (!TERMINAL.includes(j.status)) timer = setTimeout(tick, 1500);
      } catch (e) {
        setError((e as Error).message);
        timer = setTimeout(tick, 3000);
      }
    };
    tick();
    return () => { stopped = true; clearTimeout(timer); };
  }, [id, token]);

  // Live SSE — rebuilt whenever the token changes (so it carries a fresh one).
  useEffect(() => {
    if (!id || !token) return;
    const es = new EventSource(api.eventsUrl(id));
    es.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as SseEvent;
        if (ev.stage === "heartbeat") return;
        setEvents((prev) => [...prev, ev]);
        if (ev.stage === "pipeline" && (ev.status === "done" || ev.status === "error")) {
          es.close();
        }
      } catch {
        /* ignore malformed frame */
      }
    };
    es.onerror = () => { /* browser auto-reconnects; terminal close handled above */ };
    return () => es.close();
  }, [id, token]);

  return { job, events, error, refresh };
}

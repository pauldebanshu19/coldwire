"use client";

import { useEffect, useRef, useState } from "react";
import { api, type Job, type SseEvent } from "@/lib/api";

const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED"];

export function useJobStream(id: string) {
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const seen = useRef(0);

  const refresh = async () => {
    try {
      setJob(await api.getJob(id));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // Authoritative status via polling (until terminal).
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      if (stopped) return;
      try {
        const j = await api.getJob(id);
        if (stopped) return;
        setJob(j);
        if (!TERMINAL.includes(j.status)) timer = setTimeout(tick, 1500);
      } catch (e) {
        setError((e as Error).message);
        timer = setTimeout(tick, 3000);
      }
    };
    tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  // Live granular progress via SSE.
  useEffect(() => {
    const es = new EventSource(api.eventsUrl(id));
    es.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as SseEvent;
        if (ev.stage === "heartbeat") return;
        setEvents((prev) => [...prev, ev]);
        seen.current += 1;
        if (ev.stage === "pipeline" && (ev.status === "done" || ev.status === "error")) {
          es.close();
        }
      } catch {
        /* ignore malformed frame */
      }
    };
    es.onerror = () => {
      // browser auto-reconnects; terminal close handled in onmessage
    };
    return () => es.close();
  }, [id]);

  return { job, events, error, refresh };
}

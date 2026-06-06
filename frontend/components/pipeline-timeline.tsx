"use client";

import { useEffect, useRef } from "react";
import type { Job, SseEvent } from "@/lib/api";
import { STAGES, stageState, statKey, type StageState } from "@/lib/status";
import { cn } from "@/lib/utils";

const STAGE_COLOR: Record<string, string> = {
  ocean: "text-sky-400",
  prospeo: "text-violet-400",
  eazyreach: "text-amber-400",
  brevo: "text-primary",
  pipeline: "text-muted-foreground",
};
const STAGE_TAG: Record<string, string> = {
  ocean: "OCEAN", prospeo: "PROSPEO", eazyreach: "RESOLVE", brevo: "BREVO", pipeline: "SYS",
};

function StateDot({ state }: { state: StageState }) {
  if (state === "running")
    return <span className="size-2.5 rounded-full bg-primary animate-pulse-ring" />;
  if (state === "done")
    return <span className="font-mono text-xs text-primary">✓</span>;
  if (state === "failed")
    return <span className="font-mono text-xs text-destructive">✕</span>;
  return <span className="size-2 rounded-full border border-muted-foreground/40" />;
}

function StageCard({
  stage, state, count,
}: { stage: (typeof STAGES)[number]; state: StageState; count?: number }) {
  const active = state === "running";
  const lit = state === "running" || state === "done";
  return (
    <div
      className={cn(
        "relative rounded-lg border bg-card/50 p-4 transition-colors",
        active && "border-primary/50 glow-edge",
        state === "done" && "border-primary/25",
        state === "failed" && "border-destructive/40",
        state === "pending" && "border-border opacity-70",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] text-muted-foreground">{stage.n}</span>
        <StateDot state={state} />
      </div>
      <div className="mt-2 font-mono text-sm font-semibold text-foreground">{stage.label}</div>
      <div className="font-mono text-[11px] text-muted-foreground">{stage.provider}</div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className={cn("font-mono text-2xl tabnums", lit ? "text-primary" : "text-muted-foreground/40")}>
          {typeof count === "number" ? count : "—"}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
          {stage.out}
        </span>
      </div>
    </div>
  );
}

function EventLog({ events }: { events: SseEvent[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [events.length]);

  const shown = events.slice(-80);
  return (
    <div className="mt-4 overflow-hidden rounded-lg border border-border bg-background/60">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        <span className="size-1.5 rounded-full bg-primary animate-pulse" /> live feed
      </div>
      <div ref={ref} className="max-h-72 overflow-y-auto px-3 py-2 font-mono text-xs leading-relaxed">
        {shown.length === 0 && <div className="text-muted-foreground/60">waiting for events…</div>}
        {shown.map((e, i) => (
          <div key={i} className="flex gap-2.5 py-0.5">
            <span className="shrink-0 text-muted-foreground/50 tabnums">
              {new Date(e.ts * 1000).toLocaleTimeString()}
            </span>
            <span className={cn("w-16 shrink-0 tracking-wide", STAGE_COLOR[e.stage] ?? "text-muted-foreground")}>
              {STAGE_TAG[e.stage] ?? e.stage}
            </span>
            <span
              className={cn(
                "min-w-0 break-words",
                e.status === "error" ? "text-destructive"
                  : e.status === "skip" ? "text-muted-foreground/60"
                  : "text-foreground/90",
              )}
            >
              {e.message ?? e.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PipelineTimeline({ job, events }: { job: Job; events: SseEvent[] }) {
  const lastCount: Record<string, number> = {};
  for (const e of events) {
    if (typeof e.count === "number" && e.count > 0) lastCount[e.stage] = e.count;
  }
  const countFor = (key: string): number | undefined => {
    const fromStats = job.stats?.[statKey(key)];
    if (typeof fromStats === "number" && fromStats > 0) return fromStats;
    return lastCount[key];
  };

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STAGES.map((s) => (
          <StageCard key={s.key} stage={s} state={stageState(s.runAt, job.status)} count={countFor(s.key)} />
        ))}
      </div>
      <EventLog events={events} />
    </div>
  );
}

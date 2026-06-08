import type { JobStatus, JobStats } from "./api";

export const STAGES = [
  { key: "ocean", n: "01", label: "Source", provider: "Ocean.io", out: "lookalike companies", stat: "companies", runAt: "SOURCING" },
  { key: "prospeo", n: "02", label: "Prospect", provider: "Prospeo", out: "decision-makers", stat: "contacts", runAt: "PROSPECTING" },
  { key: "resolve", n: "03", label: "Resolve", provider: "Prospeo", out: "verified emails", stat: "deliverable", runAt: "RESOLVING" },
  { key: "brevo", n: "04", label: "Send", provider: "Brevo", out: "outreach sent", stat: "sent", runAt: "SENDING" },
] as const;

export type Tone = "idle" | "run" | "gate" | "ok" | "bad";

export const STATUS: Record<JobStatus, { label: string; tone: Tone }> = {
  QUEUED: { label: "Queued", tone: "idle" },
  SOURCING: { label: "Sourcing", tone: "run" },
  PROSPECTING: { label: "Prospecting", tone: "run" },
  RESOLVING: { label: "Resolving", tone: "run" },
  AWAITING_APPROVAL: { label: "Awaiting approval", tone: "gate" },
  SENDING: { label: "Sending", tone: "run" },
  COMPLETED: { label: "Completed", tone: "ok" },
  FAILED: { label: "Failed", tone: "bad" },
  CANCELLED: { label: "Cancelled", tone: "idle" },
};

const ORDER: JobStatus[] = [
  "QUEUED", "SOURCING", "PROSPECTING", "RESOLVING",
  "AWAITING_APPROVAL", "SENDING", "COMPLETED",
];

export type StageState = "pending" | "running" | "done" | "failed";

export function stageState(stageRunAt: string, jobStatus: JobStatus): StageState {
  if (jobStatus === "CANCELLED") {
    return ORDER.indexOf(stageRunAt as JobStatus) < ORDER.indexOf("AWAITING_APPROVAL")
      ? "done" : "pending";
  }
  const cur = ORDER.indexOf(jobStatus === "FAILED" ? "QUEUED" : jobStatus);
  const run = ORDER.indexOf(stageRunAt as JobStatus);
  if (jobStatus === "FAILED") return "pending";
  if (cur > run) return "done";
  if (cur === run) return "running";
  return "pending";
}

export const TONE_CLASS: Record<Tone, string> = {
  idle: "text-muted-foreground border-border",
  run: "text-primary border-primary/40",
  gate: "text-amber-400 border-amber-400/40",
  ok: "text-primary border-primary/50",
  bad: "text-destructive border-destructive/50",
};

export function statKey(stage: string): keyof JobStats {
  const s = STAGES.find((x) => x.key === stage);
  return (s?.stat ?? "companies") as keyof JobStats;
}

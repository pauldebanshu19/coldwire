import type { JobStatus } from "@/lib/api";
import { STATUS, TONE_CLASS } from "@/lib/status";
import { cn } from "@/lib/utils";

export function StatusBadge({ status, className }: { status: JobStatus; className?: string }) {
  const s = STATUS[status];
  const live = s.tone === "run";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border bg-card/60 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.2em]",
        TONE_CLASS[s.tone],
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full bg-current", live && "animate-pulse")} />
      {s.label}
    </span>
  );
}

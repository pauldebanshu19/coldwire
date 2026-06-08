import { STAGES } from "@/lib/status";

export function PipelineStrip() {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-card/50 p-5 sm:p-7">
      <div className="absolute inset-0 -z-10 bg-grid opacity-50" />
      <div className="mb-5 flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-primary">// the pipeline</span>
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">one input · four stages</span>
      </div>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
        {STAGES.map((s, i) => (
          <div key={s.key} className="flex flex-1 items-stretch gap-3">
            <div className="flex-1 rounded-xl border border-border bg-background/50 p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-muted-foreground">{s.n}</span>
                <span className="size-1.5 rounded-full bg-primary/70" />
              </div>
              <div className="mt-2 font-mono text-sm font-semibold text-foreground">{s.label}</div>
              <div className="font-mono text-[11px] text-muted-foreground">{s.provider}</div>
              <div className="mt-2 font-mono text-[10px] uppercase tracking-wide text-primary/80">{s.out}</div>
            </div>
            {i < STAGES.length - 1 && (
              <div className="hidden items-center font-mono text-border lg:flex">→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

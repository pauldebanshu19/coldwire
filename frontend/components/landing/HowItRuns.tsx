import { RUN } from "./content";
import { Reveal } from "./Reveal";

export function HowItRuns() {
  return (
    <section className="mt-16">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-primary">// how it runs</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Stage by stage, hand-off free.</h2>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {RUN.map((s, i) => (
          <Reveal key={s.n} delay={i * 90}>
            <div className="h-full rounded-xl border border-border bg-card/50 p-5 transition-colors hover:border-primary/40">
              <div className="flex items-center justify-between">
                <span className="grid size-9 place-items-center rounded-md border border-primary/30 bg-primary/10 font-mono text-xs text-primary">
                  {s.n}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{s.provider}</span>
              </div>
              <div className="mt-4 font-mono text-base font-semibold text-foreground">{s.label}</div>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

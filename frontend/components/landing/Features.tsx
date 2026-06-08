import { FEATURES } from "./content";
import { Reveal } from "./Reveal";

export function Features() {
  return (
    <section className="mt-16">
      <div className="mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-primary">// built for the job</div>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Production-grade, not a script.</h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <Reveal key={f.title} delay={i * 70}>
            <div className="group h-full rounded-xl border border-border bg-card/40 p-5 transition-colors hover:bg-card/70">
              <div className="mb-3 inline-flex size-8 items-center justify-center rounded-md border border-primary/30 bg-primary/10 font-mono text-primary">
                ✓
              </div>
              <h3 className="font-mono text-sm font-semibold text-foreground">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

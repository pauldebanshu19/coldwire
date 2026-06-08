"use client";

import Link from "next/link";
import { STAGES } from "@/lib/status";
import { STATS } from "./content";
import { Reveal } from "./Reveal";

export function Hero() {
  return (
    <section className="flex flex-col items-center py-16 text-center lg:py-24">
      <Reveal>
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/[0.07] px-3 py-1 font-mono text-[11px] uppercase tracking-[0.3em] text-primary">
          <span className="size-1.5 rounded-full bg-primary animate-pulse" />
          sourcing → mailing
        </div>
      </Reveal>

      <Reveal delay={80}>
        <h1 className="mt-6 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-tight sm:text-6xl xl:text-7xl">
          One domain in.{" "}
          <span className="text-glow text-primary">A full outreach engine</span> out.
        </h1>
      </Reveal>

      <Reveal delay={160}>
        <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Type a single company domain. Coldwire finds lookalike companies,
          surfaces decision-makers, verifies their work emails, and queues
          personalized outreach — pausing once for your approval before anything sends.
        </p>
      </Reveal>

      <Reveal delay={240}>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex h-12 items-center rounded-full bg-primary px-7 font-mono text-sm font-medium tracking-wide text-primary-foreground transition-transform hover:scale-[1.03]"
          >
            Get started →
          </Link>
          <a
            href="#features"
            className="inline-flex h-12 items-center rounded-full border border-white/12 bg-white/[0.04] px-7 font-mono text-sm text-foreground backdrop-blur transition-colors hover:bg-white/[0.09]"
          >
            See how it works
          </a>
        </div>
      </Reveal>

      <Reveal delay={320}>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2 font-mono text-xs text-muted-foreground">
          {STAGES.map((s, i) => (
            <span key={s.key} className="flex items-center gap-2">
              <span className="rounded-md border border-border bg-card/60 px-2.5 py-1.5">
                <span className="text-primary">{s.n}</span> {s.provider}
              </span>
              {i < STAGES.length - 1 && <span className="text-border">→</span>}
            </span>
          ))}
        </div>
      </Reveal>

      <Reveal delay={400}>
        <dl className="mt-12 grid w-full max-w-lg grid-cols-4 gap-3 border-t border-border pt-6">
          {STATS.map(([n, l]) => (
            <div key={l}>
              <dt className="font-mono text-2xl font-semibold tabnums text-primary sm:text-3xl">{n}</dt>
              <dd className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{l}</dd>
            </div>
          ))}
        </dl>
      </Reveal>
    </section>
  );
}

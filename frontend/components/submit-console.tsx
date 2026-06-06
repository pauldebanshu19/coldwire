"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { STAGES } from "@/lib/status";
import { Button } from "@/components/ui/button";

function normalizeDomain(d: string): string {
  return d.trim().toLowerCase()
    .replace(/^https?:\/\//, "").replace(/^www\./, "")
    .split("/")[0].split("?")[0];
}

export function SubmitConsole() {
  const router = useRouter();
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);

  const launch = async (e: React.FormEvent) => {
    e.preventDefault();
    const seed = normalizeDomain(domain);
    if (!seed || !seed.includes(".")) {
      toast.error("Enter a valid company domain — e.g. stripe.com");
      return;
    }
    setBusy(true);
    try {
      const job = await api.createJob(seed);
      toast.success(`Pipeline armed · ${seed}`);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      toast.error((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <section className="relative overflow-hidden rounded-xl border border-border bg-card/60 p-6 sm:p-8 glow-edge">
      <div className="absolute inset-0 -z-10 bg-grid opacity-50" />
      <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-primary">
        // single input · zero humans in the loop
      </div>
      <h1 className="mt-3 max-w-xl text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">
        Type one company domain.
        <span className="text-muted-foreground"> The engine does the rest.</span>
      </h1>

      <form onSubmit={launch} className="mt-6">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex flex-1 items-center gap-2 rounded-md border border-input bg-background/70 px-3 focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-ring">
            <span className="font-mono text-primary">›</span>
            <input
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="stripe.com"
              autoFocus
              className="h-12 w-full bg-transparent font-mono text-base outline-none placeholder:text-muted-foreground/60"
            />
          </div>
          <Button type="submit" disabled={busy} size="lg" className="h-12 font-mono tracking-wide">
            {busy ? "ARMING…" : "RUN PIPELINE →"}
          </Button>
        </div>
      </form>

      <div className="mt-6 flex flex-wrap items-center gap-x-2 gap-y-2 font-mono text-xs text-muted-foreground">
        {STAGES.map((s, i) => (
          <span key={s.key} className="flex items-center gap-2">
            <span className="rounded border border-border bg-background/60 px-2 py-1">
              <span className="text-primary">{s.n}</span> {s.provider}
            </span>
            {i < STAGES.length - 1 && <span className="text-border">→</span>}
          </span>
        ))}
      </div>
    </section>
  );
}

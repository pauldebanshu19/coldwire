"use client";

import { useAuth } from "@/lib/auth";
import { AppHeader } from "@/components/app-header";
import { AuthForm } from "@/components/auth-form";
import { SubmitConsole } from "@/components/submit-console";
import { JobList } from "@/components/job-list";
import { STAGES } from "@/lib/status";

function Landing() {
  return (
    <div className="grid items-center gap-10 py-8 lg:grid-cols-[1.1fr_0.9fr]">
      <div>
        <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-primary">
          sourcing → mailing · zero humans in the loop
        </div>
        <h1 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl">
          One domain in.
          <br />
          <span className="text-glow text-primary">A full outreach engine</span> out.
        </h1>
        <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground">
          Type a single company domain. The pipeline finds lookalike companies,
          surfaces decision-makers, verifies their work emails, and queues
          personalized outreach — pausing once for your approval before anything sends.
        </p>
        <ol className="mt-8 space-y-3">
          {STAGES.map((s) => (
            <li key={s.key} className="flex items-center gap-4">
              <span className="grid size-9 shrink-0 place-items-center rounded-md border border-border bg-card/60 font-mono text-xs text-primary">
                {s.n}
              </span>
              <div>
                <span className="font-mono text-sm font-semibold text-foreground">{s.label}</span>
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  {s.provider} · {s.out}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </div>
      <AuthForm />
    </div>
  );
}

function Dashboard() {
  return (
    <div className="space-y-8 py-2">
      <SubmitConsole />
      <JobList />
    </div>
  );
}

export default function Home() {
  const { token, ready } = useAuth();
  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-5">
        {!ready ? (
          <div className="py-24 text-center font-mono text-sm text-muted-foreground">loading…</div>
        ) : token ? (
          <Dashboard />
        ) : (
          <Landing />
        )}
      </main>
      <footer className="border-t border-border/60 py-6">
        <div className="mx-auto w-full max-w-6xl px-5 font-mono text-[11px] text-muted-foreground">
          Conduit · Ocean.io → Prospeo → Eazyreach → Brevo
        </div>
      </footer>
    </>
  );
}

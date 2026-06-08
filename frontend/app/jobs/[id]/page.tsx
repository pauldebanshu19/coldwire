"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useJobStream } from "@/hooks/use-job-stream";
import { AppHeader } from "@/components/app-header";
import { PipelineTimeline } from "@/components/pipeline-timeline";
import { ReviewGate } from "@/components/review-gate";
import { ResultsTable } from "@/components/results-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";

function Note({ children, tone = "muted" }: { children: React.ReactNode; tone?: "muted" | "bad" }) {
  return (
    <div
      className={
        "rounded-lg border px-5 py-4 font-mono text-sm " +
        (tone === "bad"
          ? "border-destructive/40 bg-destructive/10 text-destructive"
          : "border-border bg-card/40 text-muted-foreground")
      }
    >
      {children}
    </div>
  );
}

export default function JobPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { token, ready } = useAuth();
  const { job, events, error, refresh } = useJobStream(id ?? "", token);

  if (ready && !token) {
    return (
      <>
        <AppHeader />
        <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-center px-5 py-24 text-center">
          <p className="font-mono text-sm text-muted-foreground">Sign in to view this run.</p>
          <Link href="/" className="mt-4">
            <Button variant="outline" className="font-mono">← Go to sign in</Button>
          </Link>
        </main>
      </>
    );
  }

  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-5 py-8">
        <div>
          <Link href="/" className="font-mono text-xs text-muted-foreground transition-colors hover:text-primary">
            ← all runs
          </Link>
          <div className="mt-3 flex items-center justify-between gap-4">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-primary">seed domain</div>
              <h1 className="font-mono text-2xl font-semibold tracking-tight">{job?.seed_domain ?? id}</h1>
            </div>
            {job && <StatusBadge status={job.status} />}
          </div>
        </div>

        {error && !job && <Note tone="bad">{error}</Note>}

        {job ? (
          <>
            <PipelineTimeline job={job} events={events} />

            {job.status === "AWAITING_APPROVAL" && <ReviewGate jobId={job.id} onChange={refresh} />}
            {job.status === "SENDING" && <Note>Sending outreach… results will appear here.</Note>}
            {job.status === "COMPLETED" && <ResultsTable jobId={job.id} seed={job.seed_domain} />}
            {job.status === "CANCELLED" && <Note>Cancelled at the gate — zero emails sent.</Note>}
            {job.status === "FAILED" && <Note tone="bad">{job.error ?? "Pipeline failed."}</Note>}
          </>
        ) : (
          <div className="h-44 animate-pulse rounded-xl border border-border bg-card/40" />
        )}
      </main>
    </>
  );
}

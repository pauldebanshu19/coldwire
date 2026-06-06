"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { api, type Job } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export function JobList() {
  const [jobs, setJobs] = useState<Job[] | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => api.listJobs().then((j) => alive && setJobs(j)).catch(() => alive && setJobs([]));
    load();
    const t = setInterval(load, 4000); // refresh history while runs progress
    return () => { alive = false; clearInterval(t); };
  }, []);

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          // run history
        </h2>
        {jobs && <span className="font-mono text-xs text-muted-foreground">{jobs.length} runs</span>}
      </div>

      {jobs === null ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg border border-border bg-card/40" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-card/30 px-5 py-10 text-center">
          <p className="font-mono text-sm text-muted-foreground">No runs yet. Launch one above.</p>
        </div>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card/40">
          {jobs.map((j) => (
            <li key={j.id}>
              <Link
                href={`/jobs/${j.id}`}
                className="group flex items-center justify-between gap-4 px-4 py-3 transition-colors hover:bg-accent/40"
              >
                <div className="min-w-0">
                  <div className="truncate font-mono text-sm text-foreground group-hover:text-primary">
                    {j.seed_domain}
                  </div>
                  <div className="mt-0.5 font-mono text-[11px] text-muted-foreground tabnums">
                    {j.stats?.companies ?? 0}c · {j.stats?.contacts ?? 0}p · {j.stats?.deliverable ?? 0}✓
                    {typeof j.stats?.sent === "number" && ` · ${j.stats.sent} sent`}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  {j.created_at && (
                    <span className="hidden font-mono text-[11px] text-muted-foreground sm:inline">
                      {formatDistanceToNow(new Date(j.created_at), { addSuffix: true })}
                    </span>
                  )}
                  <StatusBadge status={j.status} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

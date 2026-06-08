"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { api, type Job } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" className="size-4">
      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

export function JobList() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [target, setTarget] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => api.listJobs().then((j) => alive && setJobs(j)).catch(() => alive && setJobs([]));
    load();
    const t = setInterval(load, 4000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const confirmDelete = async () => {
    if (!target) return;
    setBusy(true);
    try {
      await api.deleteJob(target.id);
      setJobs((j) => j?.filter((x) => x.id !== target.id) ?? null);
      toast.success(`Deleted run · ${target.seed_domain}`);
      setTarget(null);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

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
            <li key={j.id} className="flex items-center gap-1 pr-2 transition-colors hover:bg-accent/40">
              <Link href={`/jobs/${j.id}`} className="group flex min-w-0 flex-1 items-center justify-between gap-4 px-4 py-3">
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
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setTarget(j); }}
                aria-label={`Delete run ${j.seed_domain}`}
                title="Delete run"
                className="grid size-8 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive"
              >
                <TrashIcon />
              </button>
            </li>
          ))}
        </ul>
      )}

      <AlertDialog open={!!target} onOpenChange={(o) => !o && setTarget(null)}>
        <AlertDialogContent className="border-border bg-card">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-mono">
              Delete run · <span className="text-primary">{target?.seed_domain}</span>
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>Permanently removes this run and everything it produced:</p>
                <ul className="font-mono text-xs">
                  <li>· {target?.stats?.companies ?? 0} companies</li>
                  <li>· {target?.stats?.contacts ?? 0} contacts</li>
                  <li>· {target?.stats?.deliverable ?? 0} resolved emails</li>
                  <li>· {target?.stats?.sent ?? 0} sent records</li>
                </ul>
                <p>This cannot be undone.</p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy} className="font-mono">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => { e.preventDefault(); confirmDelete(); }}
              disabled={busy}
              className="bg-destructive font-mono text-white hover:bg-destructive/90"
            >
              {busy ? "Deleting…" : "Delete run"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}

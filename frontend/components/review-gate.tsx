"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type Review } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function Tile({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="rounded-md border border-border bg-background/50 px-3 py-3">
      <div className={cn("font-mono text-2xl font-semibold tabnums", accent ? "text-primary" : "text-foreground")}>
        {value}
      </div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
    </div>
  );
}

export function ReviewGate({ jobId, onChange }: { jobId: string; onChange: () => void }) {
  const [review, setReview] = useState<Review | null>(null);
  const [busy, setBusy] = useState<"" | "approve" | "cancel">("");

  useEffect(() => {
    api.review(jobId).then(setReview).catch((e) => toast.error((e as Error).message));
  }, [jobId]);

  const approve = async () => {
    setBusy("approve");
    try {
      await api.approve(jobId);
      toast.success("Approved — firing outreach");
      onChange();
    } catch (e) {
      toast.error((e as Error).message);
      setBusy("");
    }
  };
  const cancel = async () => {
    setBusy("cancel");
    try {
      await api.cancel(jobId);
      toast("Cancelled — zero emails sent");
      onChange();
    } catch (e) {
      toast.error((e as Error).message);
      setBusy("");
    }
  };

  return (
    <section className="overflow-hidden rounded-xl border border-amber-400/40 bg-card/60">
      <div className="flex items-center gap-2 border-b border-amber-400/30 bg-amber-400/5 px-5 py-3 font-mono text-[11px] uppercase tracking-[0.25em] text-amber-400">
        <span className="size-1.5 rounded-full bg-amber-400 animate-pulse" />
        safety checkpoint · nothing sent yet
      </div>

      <div className="p-5">
        {!review ? (
          <div className="h-28 animate-pulse rounded-md bg-background/40" />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Tile label="companies" value={review.companies} />
              <Tile label="contacts" value={review.contacts} />
              <Tile label="deliverable" value={review.deliverable} accent />
              <Tile label="skipped" value={review.skipped} />
            </div>

            {review.sample_subject && (
              <div className="mt-5 overflow-hidden rounded-md border border-border bg-background/60">
                <div className="border-b border-border px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  sample · rendered for one real contact
                </div>
                <div className="space-y-2 px-4 py-3 font-mono text-xs">
                  <div><span className="text-muted-foreground">To: </span>{review.sample_to}</div>
                  <div><span className="text-muted-foreground">Subject: </span><span className="text-foreground">{review.sample_subject}</span></div>
                  <pre className="mt-2 whitespace-pre-wrap break-words text-foreground/85">{review.sample_body}</pre>
                </div>
              </div>
            )}

            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button
                onClick={approve}
                disabled={busy !== "" || review.deliverable === 0}
                size="lg"
                className="font-mono tracking-wide"
              >
                {busy === "approve" ? "FIRING…" : `APPROVE & SEND ${review.deliverable} →`}
              </Button>
              <Button
                onClick={cancel}
                disabled={busy !== ""}
                variant="outline"
                size="lg"
                className="font-mono tracking-wide border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                {busy === "cancel" ? "CANCELLING…" : "CANCEL"}
              </Button>
              {review.deliverable === 0 && (
                <span className="font-mono text-xs text-muted-foreground">No deliverable emails to send.</span>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

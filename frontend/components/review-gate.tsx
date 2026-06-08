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
  const [senderName, setSenderName] = useState("");
  const [replyTo, setReplyTo] = useState("");

  useEffect(() => {
    api.review(jobId).then(setReview).catch((e) => toast.error((e as Error).message));
  }, [jobId]);

  const approve = async () => {
    if (replyTo.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(replyTo.trim())) {
      toast.error("Reply-to must be a valid email");
      return;
    }
    setBusy("approve");
    try {
      await api.approve(jobId, { sender_name: senderName, reply_to: replyTo });
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

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Sender name
                </label>
                <input
                  value={senderName}
                  onChange={(e) => setSenderName(e.target.value)}
                  placeholder="Coldwire"
                  className="h-10 w-full rounded-md border border-input bg-background/70 px-3 font-mono text-sm outline-none focus:border-primary/60 focus:ring-2 focus:ring-ring placeholder:text-muted-foreground/50"
                />
              </div>
              <div className="space-y-1.5">
                <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Reply-to email
                </label>
                <input
                  type="email"
                  value={replyTo}
                  onChange={(e) => setReplyTo(e.target.value)}
                  placeholder="replies@yourdomain.com"
                  className="h-10 w-full rounded-md border border-input bg-background/70 px-3 font-mono text-sm outline-none focus:border-primary/60 focus:ring-2 focus:ring-ring placeholder:text-muted-foreground/50"
                />
              </div>
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-muted-foreground/70">
              From stays your verified sender; only the display name + reply-to change.
            </p>

            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
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

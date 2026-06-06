"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type Results, type ResultRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PILL: Record<ResultRow["status"], string> = {
  SENT: "text-primary border-primary/40 bg-primary/10",
  FAILED: "text-destructive border-destructive/40 bg-destructive/10",
  SKIPPED: "text-muted-foreground border-border bg-muted/30",
};

function csvCell(v: string): string {
  return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

function exportCsv(rows: ResultRow[], seed: string) {
  const header = ["contact", "email", "status", "message_id", "error"];
  const lines = [
    header.join(","),
    ...rows.map((r) =>
      [r.contact, r.email ?? "", r.status, r.message_id ?? "", r.error ?? ""].map(csvCell).join(","),
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `conduit-${seed}-results.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function Tile({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-md border border-border bg-background/50 px-3 py-3">
      <div className={cn("font-mono text-2xl font-semibold tabnums", tone)}>{value}</div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
    </div>
  );
}

export function ResultsTable({ jobId, seed }: { jobId: string; seed: string }) {
  const [data, setData] = useState<Results | null>(null);

  useEffect(() => {
    api.results(jobId).then(setData).catch((e) => toast.error((e as Error).message));
  }, [jobId]);

  if (!data) return <div className="h-32 animate-pulse rounded-xl border border-border bg-card/40" />;

  const s = data.stats;
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card/50">
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">// results</h2>
        <Button
          variant="outline" size="sm"
          onClick={() => exportCsv(data.results, seed)}
          disabled={data.results.length === 0}
          className="font-mono text-xs"
        >
          export csv
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3 p-5">
        <Tile label="sent" value={s.sent ?? 0} tone="text-primary" />
        <Tile label="failed" value={s.failed ?? 0} tone="text-destructive" />
        <Tile label="skipped" value={s.skipped ?? 0} tone="text-muted-foreground" />
      </div>

      {data.results.length > 0 && (
        <div className="max-h-96 overflow-y-auto border-t border-border">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card/95 backdrop-blur">
              <tr className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                <th className="px-5 py-2 text-left font-medium">Contact</th>
                <th className="px-5 py-2 text-left font-medium">Email</th>
                <th className="px-5 py-2 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.results.map((r, i) => (
                <tr key={i} className="hover:bg-accent/30">
                  <td className="px-5 py-2.5 font-medium">{r.contact}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-muted-foreground">
                    {r.email ?? "—"}
                    {r.error && <span className="block text-destructive">{r.error}</span>}
                  </td>
                  <td className="px-5 py-2.5 text-right">
                    <span className={cn("inline-block rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase", PILL[r.status])}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

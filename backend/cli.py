#!/usr/bin/env python3
"""Coldwire CLI — the gradeable core, run live.

    python cli.py acme.com                 # real APIs, prompts before sending
    python cli.py acme.com --mock          # fake providers, zero credits
    python cli.py acme.com --dry-run       # run all 3 stages, stop at the gate
    python cli.py acme.com --yes           # non-interactive approve (careful)
    python cli.py acme.com --out out.csv   # export results

One domain in -> Ocean -> Prospeo -> Eazyreach -> [approve] -> Brevo.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import fresh_settings
from core.logging import redact_email, setup_logging
from core.models import PipelineResult, Review, normalize_domain
from core.pipeline import run_pipeline

console = Console()

STAGE_STYLE = {
    "ocean": ("Ocean", "cyan"),
    "prospeo": ("Prospeo", "magenta"),
    "eazyreach": ("Resolve", "yellow"),
    "brevo": ("Brevo", "green"),
    "pipeline": ("Pipeline", "bold blue"),
}
ICON = {"start": "▶", "progress": "·", "done": "✓", "skip": "→", "error": "✗"}


def on_event(stage: str, status: str, count: int, message: str) -> None:
    label, color = STAGE_STYLE.get(stage, (stage, "white"))
    icon = ICON.get(status, "·")
    suffix = f" [dim]({count})[/dim]" if count and status in ("progress", "done") else ""
    style = "red" if status == "error" else ("dim" if status in ("progress", "skip") else color)
    console.print(f"  [{color}]{icon} {label:<8}[/{color}] [{style}]{message}[/{style}]{suffix}")


def make_approver(auto_yes: bool, dry_run: bool):
    def approve(review: Review) -> bool:
        _print_review(review)
        if dry_run:
            console.print("\n[yellow]--dry-run: stopping at the gate. Nothing sent.[/yellow]")
            return False
        if review.deliverable == 0:
            console.print("\n[yellow]No deliverable emails — nothing to send.[/yellow]")
            return False
        if auto_yes:
            console.print("\n[bold]--yes: auto-approved.[/bold]")
            return True
        try:
            answer = console.input(
                f"\n[bold]Send {review.deliverable} emails? [/bold][dim]\\[y/N][/dim] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")

    return approve


def _print_review(review: Review) -> None:
    table = Table(title="Approval checkpoint", title_style="bold", show_header=True,
                  header_style="bold")
    table.add_column("Companies", justify="right")
    table.add_column("Contacts", justify="right")
    table.add_column("Deliverable", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_row(str(review.companies), str(review.contacts),
                  str(review.deliverable), str(review.skipped))
    console.print()
    console.print(table)
    if review.sample_subject:
        body = (review.sample_body or "")[:700]
        console.print(Panel(
            f"[bold]To:[/bold] {redact_email(review.sample_to)}\n"
            f"[bold]Subject:[/bold] {review.sample_subject}\n\n{body}",
            title="Sample email (1 real contact)", border_style="dim",
        ))


def _print_results(result: PipelineResult) -> None:
    s = result.stats
    console.print()
    color = {"COMPLETED": "green", "CANCELLED": "yellow", "FAILED": "red"}.get(result.status, "white")
    console.print(Panel(
        f"[bold]Status:[/bold] [{color}]{result.status}[/{color}]"
        + (f"\n[red]{result.error}[/red]" if result.error else "")
        + f"\n\ncompanies {s['companies']} · contacts {s['contacts']} · "
          f"deliverable {s['deliverable']}\n"
          f"sent [green]{s['sent']}[/green] · failed [red]{s['failed']}[/red] · "
          f"skipped [yellow]{s['skipped']}[/yellow]",
        title="Run summary", border_style=color,
    ))
    failures = [r for r in result.results if r.error]
    for r in failures[:10]:
        console.print(f"  [red]✗ {r.contact_name}[/red] {redact_email(r.email)}: {r.error}")


def write_csv(result: PipelineResult, path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["contact", "email", "status", "message_id", "error", "skipped_reason"])
        for r in result.results:
            w.writerow([r.contact_name, r.email or "", r.status.value,
                        r.message_id or "", r.error or "", r.skipped_reason or ""])
    console.print(f"[dim]Results written to {path}[/dim]")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Automated cold-outreach pipeline (one domain in).")
    p.add_argument("seed_domain", help="seed company domain, e.g. acme.com")
    p.add_argument("--mock", action="store_true", help="use fake providers (zero credits)")
    p.add_argument("--dry-run", action="store_true", help="run stages 1-3, stop at the gate")
    p.add_argument("--yes", action="store_true", help="auto-approve sending (non-interactive)")
    p.add_argument("--max-companies", type=int, default=None)
    p.add_argument("--max-contacts", type=int, default=None, dest="max_contacts_per_company")
    p.add_argument("--out", default=None, help="write results CSV to this path")
    p.add_argument("--log-level", default=None)
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    seed = normalize_domain(args.seed_domain)
    if not seed or "." not in seed:
        console.print(f"[red]Invalid seed domain: {args.seed_domain!r}[/red]")
        return 2

    settings = fresh_settings(
        mock=args.mock or None,
        max_companies=args.max_companies,
        max_contacts_per_company=args.max_contacts_per_company,
        log_level=args.log_level,
    )
    setup_logging(settings.log_level)

    console.print(Panel(
        f"[bold]seed[/bold] {seed}    [dim]mode[/dim] {'MOCK' if settings.mock else 'LIVE'}    "
        f"[dim]brevo[/dim] {settings.resolved_brevo_transport}",
        title="Coldwire — cold-outreach pipeline", border_style="blue",
    ))

    result = asyncio.run(run_pipeline(
        settings, seed,
        on_event=on_event,
        approve=make_approver(args.yes, args.dry_run),
    ))

    _print_results(result)
    if args.out:
        write_csv(result, args.out)
    return 0 if result.status in ("COMPLETED", "CANCELLED") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

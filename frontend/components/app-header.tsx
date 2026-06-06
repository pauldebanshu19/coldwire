"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  const { email, logout } = useAuth();
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-md border border-primary/40 bg-primary/10 glow-edge">
            <span className="size-2 rounded-full bg-primary animate-pulse" />
          </span>
          <span className="leading-none">
            <span className="block font-mono text-sm font-semibold tracking-[0.28em] text-foreground">
              CONDUIT
            </span>
            <span className="mt-1 block font-mono text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
              outreach engine
            </span>
          </span>
        </Link>
        {email && (
          <div className="flex items-center gap-3">
            <span className="hidden font-mono text-xs text-muted-foreground sm:inline">{email}</span>
            <Button variant="ghost" size="sm" onClick={logout} className="font-mono text-xs">
              sign out
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}

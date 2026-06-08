"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  const { email, signOut } = useAuth();
  const router = useRouter();

  const handleSignOut = async () => {
    await signOut();
    router.push("/"); // back to the landing
  };
  return (
    <header className="sticky top-0 z-40 px-3 pt-3 sm:px-5 sm:pt-4">
      <div
        className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.045] px-4 shadow-[0_8px_30px_-12px_rgba(0,0,0,0.6)] backdrop-blur-xl backdrop-saturate-150 supports-[backdrop-filter]:bg-white/[0.045] sm:px-5"
      >
        <Link href="/" className="flex items-center gap-3">
          <span className="grid size-8 place-items-center rounded-lg border border-primary/40 bg-primary/10 glow-edge">
            <span className="size-2 rounded-full bg-primary animate-pulse" />
          </span>
          <span className="leading-none">
            <span className="block font-mono text-sm font-semibold tracking-[0.28em] text-foreground">
              COLDWIRE
            </span>
            <span className="mt-0.5 hidden font-mono text-[10px] uppercase tracking-[0.32em] text-muted-foreground sm:block">
              outreach engine
            </span>
          </span>
        </Link>

        {email && (
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 font-mono text-xs text-muted-foreground sm:inline-flex">
              <span className="size-1.5 rounded-full bg-primary" />
              {email}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSignOut}
              className="rounded-full border border-white/10 bg-white/[0.03] font-mono text-xs hover:bg-white/[0.08]"
            >
              sign out
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}

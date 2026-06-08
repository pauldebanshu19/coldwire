"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function Navbar() {
  const { token, signOut } = useAuth();
  const router = useRouter();

  const handleSignOut = async () => {
    await signOut();
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-40 px-3 pt-3 sm:px-5 sm:pt-4">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.045] px-4 shadow-[0_8px_30px_-12px_rgba(0,0,0,0.7)] backdrop-blur-xl backdrop-saturate-150 sm:px-5">
        <a href="#top" className="flex items-center gap-2.5">
          <span className="grid size-7 place-items-center rounded-lg border border-primary/40 bg-primary/10 glow-edge">
            <span className="size-2 rounded-full bg-primary animate-pulse" />
          </span>
          <span className="font-mono text-sm font-semibold tracking-[0.28em] text-foreground">COLDWIRE</span>
        </a>

        <nav className="flex items-center gap-2">
          {token ? (
            <button
              onClick={handleSignOut}
              className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 font-mono text-xs text-foreground transition-colors hover:bg-white/[0.09]"
            >
              Sign out
            </button>
          ) : (
            <Link
              href="/login"
              className="rounded-full bg-primary px-4 py-2 font-mono text-xs font-medium tracking-wide text-primary-foreground transition-transform hover:scale-[1.03]"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

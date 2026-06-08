"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  const { token, ready } = useAuth();
  const router = useRouter();

  // Once authenticated, leave the login page for the dashboard.
  useEffect(() => {
    if (ready && token) router.replace("/");
  }, [ready, token, router]);

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center px-5 py-16">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="absolute left-1/2 top-[-10%] h-[50vh] w-[70vw] -translate-x-1/2 rounded-full bg-primary/10 blur-[120px]" />
      </div>

      <Link
        href="/"
        className="mb-6 flex items-center gap-2.5"
      >
        <span className="grid size-8 place-items-center rounded-lg border border-primary/40 bg-primary/10 glow-edge">
          <span className="size-2 rounded-full bg-primary animate-pulse" />
        </span>
        <span className="font-mono text-sm font-semibold tracking-[0.28em] text-foreground">COLDWIRE</span>
      </Link>

      <div className="w-full max-w-md">
        <AuthForm />
      </div>

      <Link href="/" className="mt-6 font-mono text-xs text-muted-foreground transition-colors hover:text-primary">
        ← back to home
      </Link>
    </main>
  );
}

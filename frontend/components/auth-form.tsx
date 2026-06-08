"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38Z" />
    </svg>
  );
}

export function AuthForm() {
  const { signIn, signUp, signInWithGoogle } = useAuth();
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const google = async () => {
    try {
      await signInWithGoogle();
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        await signIn(email, password);
        toast.success("Signed in");
      } else {
        const active = await signUp(email, password);
        if (active) {
          toast.success("Account created");
        } else {
          toast.message("Check your email to confirm, then sign in.");
          setMode("login");
        }
      }
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-card/70 p-8 glow-edge">
      <div className="absolute inset-0 -z-10 bg-grid opacity-60" />
      <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.3em] text-primary">
        {mode === "register" ? "// new operator" : "// authenticate"}
      </div>
      <h2 className="font-mono text-2xl font-semibold tracking-tight text-foreground">
        {mode === "register" ? "Create access" : "Sign in"}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Secured by Supabase Auth. Your email is your tenant key.
      </p>

      <Button
        type="button" variant="outline" onClick={google}
        className="mt-6 w-full gap-2 bg-background/60 font-mono"
      >
        <GoogleIcon />
        Continue with Google
      </Button>

      <div className="my-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">or</span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <form onSubmit={submit} className="space-y-3">
        <div className="space-y-1.5">
          <label className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">Email</label>
          <Input
            type="email" required value={email} autoComplete="email"
            onChange={(e) => setEmail(e.target.value)} placeholder="you@yourdomain.com"
            className="font-mono"
          />
        </div>
        <div className="space-y-1.5">
          <label className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">Password</label>
          <Input
            type="password" required minLength={6} value={password}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            onChange={(e) => setPassword(e.target.value)} placeholder="min. 6 characters"
            className="font-mono"
          />
        </div>
        <Button type="submit" disabled={busy} className="w-full font-mono tracking-wide">
          {busy ? "…" : mode === "register" ? "Create & enter" : "Enter"}
        </Button>
      </form>

      <button
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="mt-4 font-mono text-xs text-muted-foreground transition-colors hover:text-primary"
      >
        {mode === "login" ? "No account? Create one →" : "Already have access? Sign in →"}
      </button>
    </div>
  );
}

"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function AuthForm() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      toast.success(mode === "login" ? "Signed in" : "Account created");
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
        Tokenized access to the outreach pipeline. Use any email — it&apos;s your tenant key.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-3">
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
            type="password" required minLength={8} value={password}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            onChange={(e) => setPassword(e.target.value)} placeholder="min. 8 characters"
            className="font-mono"
          />
        </div>
        <Button type="submit" disabled={busy} className="w-full font-mono tracking-wide">
          {busy ? "…" : mode === "register" ? "Create & enter" : "Enter"}
        </Button>
      </form>

      <button
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className={cn("mt-4 font-mono text-xs text-muted-foreground transition-colors hover:text-primary")}
      >
        {mode === "login" ? "No account? Create one →" : "Already have access? Sign in →"}
      </button>
    </div>
  );
}

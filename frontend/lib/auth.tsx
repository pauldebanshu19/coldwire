"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { setBearer } from "./api";

interface AuthCtx {
  token: string | null;
  email: string | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  /** returns true if a session was created immediately (no email confirmation) */
  signUp: (email: string, password: string) => Promise<boolean>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const apply = (session: Session | null) => {
    const t = session?.access_token ?? null;
    setBearer(t);
    setTok(t);
    setEmail(session?.user?.email ?? null);
  };

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      apply(data.session);
      setReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => apply(session));
    return () => sub.subscription.unsubscribe();
  }, []);

  const signIn = async (em: string, pw: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email: em, password: pw });
    if (error) throw new Error(error.message);
  };

  const signUp = async (em: string, pw: string) => {
    const { data, error } = await supabase.auth.signUp({ email: em, password: pw });
    if (error) throw new Error(error.message);
    return data.session != null; // false => email confirmation required
  };

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: typeof window !== "undefined" ? window.location.origin : undefined,
      },
    });
    if (error) throw new Error(error.message);
    // browser now redirects to Google; session is picked up on return.
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    apply(null);
  };

  return (
    <Ctx.Provider value={{ token, email, ready, signIn, signUp, signInWithGoogle, signOut }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}

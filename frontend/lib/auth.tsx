"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, clearToken, getToken, setToken } from "./api";

interface AuthCtx {
  token: string | null;
  email: string | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);
const EMAIL_KEY = "conduit_email";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (t) {
      setTok(t);
      setEmail(window.localStorage.getItem(EMAIL_KEY));
    }
    setReady(true);
  }, []);

  const finish = (t: string, em: string) => {
    setToken(t);
    window.localStorage.setItem(EMAIL_KEY, em);
    setTok(t);
    setEmail(em);
  };

  const login = async (em: string, pw: string) => {
    const { access_token } = await api.login(em, pw);
    finish(access_token, em);
  };
  const register = async (em: string, pw: string) => {
    const { access_token } = await api.register(em, pw);
    finish(access_token, em);
  };
  const logout = () => {
    clearToken();
    window.localStorage.removeItem(EMAIL_KEY);
    setTok(null);
    setEmail(null);
  };

  return (
    <Ctx.Provider value={{ token, email, ready, login, register, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}

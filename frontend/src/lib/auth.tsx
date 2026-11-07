import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, getToken, setToken, type User } from "./api";
import type { Lang } from "./i18n";

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  lang: Lang;
  setLang: (l: Lang) => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

/** Demo users seeded by the backend (password = "<user>-demo-pass"). */
export const DEMO_USERS: { username: string; password: string; role: string }[] = [
  { username: "agus", password: "agus-demo-pass", role: "admin" },
  { username: "budi", password: "budi-demo-pass", role: "manager" },
  { username: "hana", password: "hana-demo-pass", role: "hr" },
  { username: "dewi", password: "dewi-demo-pass", role: "finance" },
  { username: "siti", password: "siti-demo-pass", role: "employee" },
];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lang, setLang] = useState<Lang>("id");

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch {
        setToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setError(null);
    try {
      const res = await api.login(username, password);
      setToken(res.access_token);
      setUser({ username: res.username, role: res.role, department: res.department });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "login failed";
      setError(msg);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, lang, setLang, login, logout }),
    [user, loading, error, lang, login, logout],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function canUpload(role: string): boolean {
  return role === "admin" || role === "manager" || role === "hr";
}

export function canEditPolicy(role: string): boolean {
  return role === "admin" || role === "manager";
}

export function canViewSecurity(role: string): boolean {
  return role === "admin" || role === "manager";
}

export function isAdmin(role: string): boolean {
  return role === "admin";
}

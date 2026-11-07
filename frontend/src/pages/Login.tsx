import { useState } from "react";
import type { FormEvent } from "react";
import { DEMO_USERS, useAuth } from "../lib/auth";
import { t } from "../lib/i18n";
import { RoleBadge } from "../components/ui";

export default function Login() {
  const { login, error, lang, setLang } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy("form");
    try {
      await login(username.trim(), password);
    } catch {
      /* error surfaced via context */
    } finally {
      setBusy(null);
    }
  }

  async function demoLogin(u: string, p: string) {
    setBusy(u);
    try {
      await login(u, p);
    } catch {
      /* error surfaced via context */
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-indigo-600 text-xl font-black text-slate-950">
            N
          </div>
          <h1 className="text-2xl font-bold tracking-tight">NEXUS</h1>
          <p className="mt-1 text-sm text-slate-400">{t(lang, "tagline")}</p>
          <div className="mt-3 inline-flex rounded-full border border-slate-700 bg-slate-900 p-0.5 text-xs font-semibold">
            {(["id", "en"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={`rounded-full px-3 py-1 uppercase ${lang === l ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500 hover:text-slate-300"}`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400" htmlFor="username">
                {t(lang, "username")}
              </label>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none placeholder:text-slate-600 focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400" htmlFor="password">
                {t(lang, "password")}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none placeholder:text-slate-600 focus:border-cyan-500"
              />
            </div>
            {error && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={busy !== null}
              className="w-full rounded-xl bg-cyan-500 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
            >
              {busy === "form" ? "…" : t(lang, "login")}
            </button>
          </form>

          <div className="mt-6">
            <div className="mb-2 text-xs font-medium tracking-wide text-slate-500 uppercase">
              {t(lang, "demoLogins")}
            </div>
            <div className="grid grid-cols-1 gap-2">
              {DEMO_USERS.map((d) => (
                <button
                  key={d.username}
                  onClick={() => demoLogin(d.username, d.password)}
                  disabled={busy !== null}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm hover:border-cyan-500/50 disabled:opacity-50"
                >
                  <span className="font-mono">
                    {busy === d.username ? "…" : d.username}
                    <span className="ml-2 text-xs text-slate-500">{d.password}</span>
                  </span>
                  <RoleBadge role={d.role} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

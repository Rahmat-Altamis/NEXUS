import { useState } from "react";
import { AuthProvider, canViewSecurity, useAuth } from "./lib/auth";
import { t, type Lang } from "./lib/i18n";
import { RoleBadge, Spinner } from "./components/ui";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Knowledge from "./pages/Knowledge";
import Assistant from "./pages/Assistant";
import Security from "./pages/Security";

type Tab = "dashboard" | "knowledge" | "assistant" | "security";

const TABS: { id: Tab; icon: string }[] = [
  { id: "dashboard", icon: "◈" },
  { id: "knowledge", icon: "▤" },
  { id: "assistant", icon: "✦" },
  { id: "security", icon: "⛨" },
];

function tabLabel(lang: Lang, id: Tab): string {
  switch (id) {
    case "dashboard":
      return t(lang, "dashboard");
    case "knowledge":
      return t(lang, "knowledge");
    case "assistant":
      return t(lang, "assistant");
    case "security":
      return t(lang, "security");
  }
}

function Shell() {
  const { user, loading, logout, lang, setLang } = useAuth();
  const [tab, setTab] = useState<Tab>("dashboard");

  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <Spinner label="Connecting…" />
      </div>
    );
  }
  if (!user) return <Login />;

  const visibleTabs = TABS.filter((tb) => tb.id !== "security" || canViewSecurity(user.role));
  const active: Tab = visibleTabs.some((tb) => tb.id === tab) ? tab : "dashboard";

  return (
    <div className="min-h-full">
      {/* Top bar */}
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-indigo-600 text-lg font-black text-slate-950">
            N
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold tracking-tight">NEXUS</div>
            <div className="hidden truncate text-[11px] text-slate-500 sm:block">{t(lang, "tagline")}</div>
          </div>

          {/* Tab nav */}
          <nav className="mx-auto flex gap-1 rounded-full border border-slate-800 bg-slate-900 p-1" aria-label="Sections">
            {visibleTabs.map((tb) => (
              <button
                key={tb.id}
                onClick={() => setTab(tb.id)}
                className={`rounded-full px-2.5 py-1.5 text-xs font-semibold transition sm:px-4 ${
                  active === tb.id
                    ? "bg-cyan-500/20 text-cyan-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <span className="mr-1" aria-hidden>{tb.icon}</span>
                <span className="hidden md:inline">{tabLabel(lang, tb.id)}</span>
              </button>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <div className="hidden items-center gap-2 sm:flex">
              <span className="font-mono text-xs text-slate-400">{user.username}</span>
              <RoleBadge role={user.role} />
            </div>
            <div className="flex rounded-full border border-slate-700 p-0.5 text-[11px] font-bold">
              {(["id", "en"] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  className={`rounded-full px-2 py-0.5 uppercase ${lang === l ? "bg-slate-700 text-slate-100" : "text-slate-500"}`}
                >
                  {l}
                </button>
              ))}
            </div>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            >
              {t(lang, "logout")}
            </button>
          </div>
        </div>
        {/* Mobile identity row */}
        <div className="flex items-center gap-2 border-t border-slate-800/60 px-4 py-1.5 sm:hidden">
          <span className="font-mono text-xs text-slate-400">{user.username}</span>
          <RoleBadge role={user.role} />
          <span className="ml-auto text-xs font-semibold text-cyan-300">{tabLabel(lang, active)}</span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-5">
        {active === "dashboard" && <Dashboard />}
        {active === "knowledge" && <Knowledge />}
        {active === "assistant" && <Assistant />}
        {active === "security" && <Security />}
      </main>

      <footer className="mx-auto max-w-6xl px-4 pb-6 text-center text-[11px] text-slate-600">
        NEXUS · permission-aware RAG · UI hides unauthorized content — the backend enforces it.
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}

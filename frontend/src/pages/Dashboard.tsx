import { useCallback, useEffect, useState } from "react";
import { api, type DocSummary, type HistoryItem, type SecEvent, type StatsSummary } from "../lib/api";
import { canViewSecurity, isAdmin, useAuth } from "../lib/auth";
import { t } from "../lib/i18n";
import { Card, CardTitle, Empty, ErrorBanner, Spinner, StatCard, StatusPill } from "../components/ui";

export default function Dashboard() {
  const { user, lang } = useAuth();
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [docs, setDocs] = useState<DocSummary[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [secEvents, setSecEvents] = useState<SecEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [s, d, h] = await Promise.all([api.stats(), api.listDocuments(), api.chatHistory(5)]);
      setStats(s);
      setDocs(d);
      setHistory(h);
      if (user && canViewSecurity(user.role)) {
        try {
          setSecEvents(await api.securityEvents(5));
        } catch {
          setSecEvents([]);
        }
      } else {
        setSecEvents(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <Spinner label="Loading dashboard…" />;
  if (error) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!stats) return <Empty text="No data." />;

  const depts = [...new Set(docs.map((d) => d.department))];
  const active = docs.filter((d) => d.status === "active").length;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label={t(lang, "documents")} value={stats.documents} sub={`${active} active · ${stats.chunks} chunks`} />
        <StatCard label="Sources" value={depts.length} sub={depts.slice(0, 3).join(", ") || "—"} accent="text-violet-300" />
        <StatCard label={t(lang, "recentQueries")} value={stats.chat_history} sub="chat turns logged" accent="text-emerald-300" />
        <StatCard
          label={t(lang, "secEvents")}
          value={stats.security_events}
          sub={`${stats.audit_events} audit events`}
          accent={stats.security_events > 0 ? "text-rose-300" : "text-emerald-300"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardTitle right={<span className="text-xs text-slate-500">{t(lang, "ingestion")}</span>}>
            {t(lang, "documents")}
          </CardTitle>
          {docs.length === 0 ? (
            <Empty text="No documents visible to your role." />
          ) : (
            <ul className="slim-scroll max-h-64 space-y-2 overflow-y-auto">
              {docs.slice(0, 12).map((d) => (
                <li
                  key={d.id}
                  className="flex items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">#{d.id} {d.filename}</span>
                    <span className="text-xs text-slate-500">
                      {d.department} · v{d.version} · {d.effective_date || "no date"}
                    </span>
                  </span>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                      d.status === "active"
                        ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40"
                        : "bg-slate-500/15 text-slate-400 ring-slate-500/40"
                    }`}
                  >
                    {d.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-slate-500">Indexed & encrypted at ingest; chunks: {stats.chunks}.</p>
        </Card>

        <Card>
          <CardTitle>{t(lang, "recentQueries")}</CardTitle>
          {history.length === 0 ? (
            <Empty text="No queries yet — ask something in the AI Assistant tab." />
          ) : (
            <ul className="slim-scroll max-h-64 space-y-2 overflow-y-auto">
              {history.map((h) => (
                <li key={h.id} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-slate-300">{h.query}</span>
                    <StatusPill status={h.status} />
                  </div>
                  <div className="mt-1 line-clamp-2 text-xs text-slate-500">
                    {h.redacted ? `[${t(lang, "revoked")}]` : h.answer}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {secEvents !== null && (
        <Card>
          <CardTitle
            right={
              user && isAdmin(user.role) ? (
                <span className="text-xs text-slate-500">{t(lang, "auditTrail")}: {stats.audit_events}</span>
              ) : undefined
            }
          >
            {t(lang, "secEvents")} (latest)
          </CardTitle>
          {secEvents.length === 0 ? (
            <Empty text="No security events recorded." />
          ) : (
            <ul className="space-y-2">
              {secEvents.map((e) => (
                <li
                  key={e.id}
                  className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
                >
                  <span className="font-mono text-xs text-rose-300">{e.action}</span>
                  <span className="text-xs text-slate-500">by {e.user || "—"}</span>
                  <span className="ml-auto font-mono text-[11px] text-slate-600">
                    {e.ts ? new Date(e.ts).toLocaleString() : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </div>
  );
}

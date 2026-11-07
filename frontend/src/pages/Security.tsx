import { useCallback, useEffect, useState } from "react";
import { api, type SecEvent } from "../lib/api";
import { canViewSecurity, isAdmin, useAuth } from "../lib/auth";
import { t } from "../lib/i18n";
import { Card, CardTitle, Empty, ErrorBanner, Spinner } from "../components/ui";

type Tab = "security" | "audit";

export default function Security() {
  const { user, lang } = useAuth();
  const [tab, setTab] = useState<Tab>("security");
  const [secEvents, setSecEvents] = useState<SecEvent[]>([]);
  const [auditEvents, setAuditEvents] = useState<SecEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const role = user?.role ?? "";
  const admin = isAdmin(role);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [sec, audit] = await Promise.all([
        api.securityEvents(100),
        admin ? api.auditEvents(100) : Promise.resolve([] as SecEvent[]),
      ]);
      setSecEvents(sec);
      setAuditEvents(audit);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load security data");
    } finally {
      setLoading(false);
    }
  }, [admin]);

  useEffect(() => {
    if (canViewSecurity(role)) void load();
    else setLoading(false);
  }, [load, role]);

  if (!canViewSecurity(role)) {
    return (
      <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-6 py-10 text-center text-sm text-rose-200">
        {t(lang, "accessDenied")}
      </div>
    );
  }
  if (loading) return <Spinner label="Loading security console…" />;
  if (error) return <ErrorBanner message={error} onRetry={() => void load()} />;

  // Never render restricted content: only event metadata (type/user/ts/patterns).
  const injections = secEvents.filter((e) => /inject/i.test(e.action));
  const denials = auditEvents.filter((e) => /deny|denied|forbidden|revok/i.test(e.action) || /deny|denied/i.test(JSON.stringify(e.details)));
  const policyChanges = auditEvents.filter((e) => /policy|upload|delete/i.test(e.action));

  const rows = tab === "security" ? secEvents : auditEvents;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Mini label="Access decisions" value={auditEvents.length} hint="grants + checks logged" />
        <Mini label="Denials" value={denials.length} hint="blocked by policy" tone={denials.length > 0 ? "warn" : "ok"} />
        <Mini label="Injection detections" value={injections.length} hint="neutralized pre-LLM" tone={injections.length > 0 ? "bad" : "ok"} />
        <Mini label="Policy changes" value={policyChanges.length} hint="uploads / policy / deletes" />
      </div>

      <Card>
        <CardTitle
          right={
            <div className="flex rounded-full border border-slate-700 p-0.5 text-xs font-semibold">
              <button
                onClick={() => setTab("security")}
                className={`rounded-full px-3 py-1 ${tab === "security" ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500"}`}
              >
                {t(lang, "secEvents")}
              </button>
              {admin && (
                <button
                  onClick={() => setTab("audit")}
                  className={`rounded-full px-3 py-1 ${tab === "audit" ? "bg-cyan-500/20 text-cyan-300" : "text-slate-500"}`}
                >
                  {t(lang, "auditTrail")}
                </button>
              )}
            </div>
          }
        >
          {t(lang, "security")}
        </CardTitle>

        {!admin && tab === "audit" ? (
          <Empty text={t(lang, "accessDenied")} />
        ) : rows.length === 0 ? (
          <Empty text="No events recorded yet." />
        ) : (
          <ul className="slim-scroll max-h-[55vh] space-y-2 overflow-y-auto">
            {rows.map((e) => (
              <li key={`${tab}-${e.id}`} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <EventChip action={e.action} />
                  <span className="text-xs text-slate-500">user: {e.user || "—"}</span>
                  <span className="ml-auto font-mono text-[11px] text-slate-600">
                    {e.ts ? new Date(e.ts).toLocaleString() : ""}
                  </span>
                </div>
                <EventDetails details={e.details} />
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Event metadata only — document content is never rendered here. Details are PII-masked at write time.
        </p>
      </Card>
    </div>
  );
}

function Mini({ label, value, hint, tone }: { label: string; value: number; hint: string; tone?: "ok" | "warn" | "bad" }) {
  const color = tone === "bad" ? "text-rose-300" : tone === "warn" ? "text-amber-300" : "text-cyan-300";
  return (
    <Card>
      <div className="text-xs font-medium tracking-wide text-slate-400 uppercase">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>{value}</div>
      <div className="mt-0.5 text-xs text-slate-500">{hint}</div>
    </Card>
  );
}

function EventChip({ action }: { action: string }) {
  let cls = "bg-slate-500/15 text-slate-300 ring-slate-500/40";
  if (/inject|attack|malicious/i.test(action)) cls = "bg-rose-500/15 text-rose-300 ring-rose-500/40";
  else if (/deny|denied|forbidden/i.test(action)) cls = "bg-amber-500/15 text-amber-300 ring-amber-500/40";
  else if (/policy|revok|delete|upload/i.test(action)) cls = "bg-violet-500/15 text-violet-300 ring-violet-500/40";
  else if (/pii|mask/i.test(action)) cls = "bg-sky-500/15 text-sky-300 ring-sky-500/40";
  else if (/login|grant|allow/i.test(action)) cls = "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-semibold ring-1 ring-inset ${cls}`}>
      {action}
    </span>
  );
}

/** Render safe metadata only; drop anything that looks like content. */
function EventDetails({ details }: { details: Record<string, unknown> }) {
  const entries = Object.entries(details ?? {}).filter(
    ([k]) => !/content|text|answer|query|passage|embedding/i.test(k),
  );
  if (entries.length === 0) return null;
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {entries.slice(0, 8).map(([k, v]) => (
        <span key={k} className="rounded-md bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-slate-400 ring-1 ring-slate-800 ring-inset">
          {k}: {typeof v === "object" ? JSON.stringify(v).slice(0, 80) : String(v).slice(0, 80)}
        </span>
      ))}
    </div>
  );
}

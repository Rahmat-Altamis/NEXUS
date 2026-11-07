import type { ReactNode } from "react";

/* Shared presentational primitives — dark ops-console theme. */

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-sm sm:p-5 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2">
      <h3 className="text-sm font-semibold tracking-wide text-slate-300 uppercase">{children}</h3>
      {right}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  accent = "text-cyan-300",
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <Card>
      <div className="text-xs font-medium tracking-wide text-slate-400 uppercase">{label}</div>
      <div className={`mt-1 text-3xl font-bold tabular-nums ${accent}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </Card>
  );
}

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-rose-500/15 text-rose-300 ring-rose-500/40",
  manager: "bg-amber-500/15 text-amber-300 ring-amber-500/40",
  hr: "bg-violet-500/15 text-violet-300 ring-violet-500/40",
  finance: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40",
  employee: "bg-sky-500/15 text-sky-300 ring-sky-500/40",
};

export function RoleBadge({ role }: { role: string }) {
  const cls = ROLE_COLORS[role] ?? "bg-slate-500/15 text-slate-300 ring-slate-500/40";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${cls}`}>
      {role}
    </span>
  );
}

const STATUS_STYLES: Record<string, { label: string; cls: string }> = {
  ok: { label: "verified", cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40" },
  conflict: { label: "conflict", cls: "bg-amber-500/15 text-amber-300 ring-amber-500/40" },
  uncertain: { label: "uncertain", cls: "bg-sky-500/15 text-sky-300 ring-sky-500/40" },
  refused: { label: "refused", cls: "bg-rose-500/15 text-rose-300 ring-rose-500/40" },
};

export function StatusPill({ status }: { status: string }) {
  const s = STATUS_STYLES[status] ?? {
    label: status,
    cls: "bg-slate-500/15 text-slate-300 ring-slate-500/40",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${s.cls}`}>
      <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current" />
      {s.label}
    </span>
  );
}

export function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 px-4 py-8 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400" role="status">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-cyan-400" />
      {label}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <span className="break-words">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 rounded-lg bg-rose-500/20 px-3 py-1 text-xs font-semibold hover:bg-rose-500/30"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <h3 className="truncate text-sm font-semibold text-slate-100">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-lg leading-none text-slate-400 hover:bg-slate-800 hover:text-slate-100"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="slim-scroll max-h-[calc(85vh-57px)] overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

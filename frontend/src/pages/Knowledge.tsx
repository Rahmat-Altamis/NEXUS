import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, api, type DocSummary } from "../lib/api";
import { canEditPolicy, canUpload, isAdmin, useAuth } from "../lib/auth";
import { t } from "../lib/i18n";
import { Card, CardTitle, Empty, ErrorBanner, Modal, Spinner } from "../components/ui";

export default function Knowledge() {
  const { user, lang } = useAuth();
  const [docs, setDocs] = useState<DocSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<DocSummary | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [editing, setEditing] = useState<DocSummary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const role = user?.role ?? "";

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setDocs(await api.listDocuments());
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function openPreview(doc: DocSummary) {
    setPreviewLoading(true);
    setPreview({ ...doc });
    try {
      const full = await api.getDocument(doc.id, true);
      setPreview(full);
    } catch (e) {
      // Backend is source of truth: revoked docs fail here even if listed.
      setPreview(null);
      setNotice(e instanceof Error ? e.message : "preview denied");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function revoke(doc: DocSummary) {
    if (!confirm(`Revoke "${doc.filename}"? It becomes inaccessible immediately.`)) return;
    try {
      await api.updatePolicy(doc.id, { status: "revoked" });
      setNotice(`Revoked #${doc.id} ${doc.filename}`);
      void load();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "revoke failed");
    }
  }

  async function remove(doc: DocSummary) {
    if (!confirm(`Permanently delete "${doc.filename}"?`)) return;
    try {
      await api.deleteDocument(doc.id);
      setNotice(`Deleted #${doc.id}`);
      void load();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "delete failed");
    }
  }

  if (loading) return <Spinner label="Loading knowledge base…" />;

  return (
    <div className="space-y-4">
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}
      {notice && (
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200">
          {notice}
          <button onClick={() => setNotice(null)} className="ml-3 text-xs underline opacity-70">dismiss</button>
        </div>
      )}

      <p className="text-xs text-slate-500">{t(lang, "backendTruth")}</p>

      {canUpload(role) && <UploadCard onDone={() => void load()} notify={setNotice} />}

      <Card>
        <CardTitle right={<span className="text-xs text-slate-500">{docs.length} visible</span>}>
          {t(lang, "knowledge")} — {t(lang, "documents")}
        </CardTitle>
        {docs.length === 0 ? (
          <Empty text="No documents visible to your role." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs text-slate-500 uppercase">
                  <th className="py-2 pr-3 font-medium">ID</th>
                  <th className="py-2 pr-3 font-medium">File</th>
                  <th className="py-2 pr-3 font-medium">Dept</th>
                  <th className="py-2 pr-3 font-medium">Version</th>
                  <th className="py-2 pr-3 font-medium">Effective</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id} className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30">
                    <td className="py-2 pr-3 font-mono text-slate-400">#{d.id}</td>
                    <td className="py-2 pr-3 font-medium">{d.filename}</td>
                    <td className="py-2 pr-3 text-slate-400">{d.department}</td>
                    <td className="py-2 pr-3 font-mono text-slate-400">v{d.version}</td>
                    <td className="py-2 pr-3 text-slate-400">{d.effective_date || "—"}</td>
                    <td className="py-2 pr-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                          d.status === "active"
                            ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40"
                            : "bg-slate-500/15 text-slate-400 ring-slate-500/40"
                        }`}
                      >
                        {d.status}
                      </span>
                    </td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-1.5">
                        <ActionBtn onClick={() => void openPreview(d)}>Preview</ActionBtn>
                        {canEditPolicy(role) && <ActionBtn onClick={() => setEditing(d)}>Policy</ActionBtn>}
                        {canEditPolicy(role) && d.status === "active" && (
                          <ActionBtn onClick={() => void revoke(d)} danger>Revoke</ActionBtn>
                        )}
                        {isAdmin(role) && (
                          <ActionBtn onClick={() => void remove(d)} danger>Delete</ActionBtn>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {preview && (
        <Modal title={`#${preview.id} ${preview.filename}`} onClose={() => setPreview(null)}>
          {previewLoading ? (
            <Spinner label="Decrypting preview…" />
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="rounded bg-slate-800 px-2 py-0.5">{preview.department}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5">v{preview.version}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5">{preview.status}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5">{preview.source_type}</span>
              </div>
              <pre className="slim-scroll max-h-[50vh] overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs whitespace-pre-wrap text-slate-300">
                {preview.text || "(no text extracted)"}
              </pre>
              <details className="text-xs">
                <summary className="cursor-pointer text-slate-500">access_policy JSON</summary>
                <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-2 font-mono text-slate-400">
                  {JSON.stringify(preview.access_policy ?? {}, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </Modal>
      )}

      {editing && (
        <PolicyModal
          doc={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void load();
          }}
          notify={setNotice}
        />
      )}
    </div>
  );
}

function ActionBtn({
  children,
  onClick,
  danger,
}: {
  children: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-2 py-1 text-xs font-semibold ring-1 ring-inset ${
        danger
          ? "bg-rose-500/10 text-rose-300 ring-rose-500/30 hover:bg-rose-500/20"
          : "bg-slate-800 text-slate-300 ring-slate-700 hover:bg-slate-700"
      }`}
    >
      {children}
    </button>
  );
}

function UploadCard({ onDone, notify }: { onDone: () => void; notify: (m: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [department, setDepartment] = useState("general");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    try {
      const doc = await api.uploadDocument(file, { department, author: "", effective_date: effectiveDate });
      notify(`Uploaded #${doc.id} ${doc.filename} — parsed, encrypted & indexed.`);
      setFile(null);
      onDone();
    } catch (err) {
      notify(err instanceof Error ? err.message : "upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardTitle>Upload document</CardTitle>
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex-1">
          <span className="mb-1 block text-xs text-slate-400">File (pdf, docx, txt, md, csv)</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md,.csv,.json"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-500/20 file:px-3 file:py-1 file:text-xs file:font-bold file:text-cyan-300"
          />
        </label>
        <label>
          <span className="mb-1 block text-xs text-slate-400">Department</span>
          <input
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-500 sm:w-40"
          />
        </label>
        <label>
          <span className="mb-1 block text-xs text-slate-400">Effective date</span>
          <input
            value={effectiveDate}
            onChange={(e) => setEffectiveDate(e.target.value)}
            placeholder="2026-01-15"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-500 sm:w-40"
          />
        </label>
        <button
          type="submit"
          disabled={!file || busy}
          className="rounded-xl bg-cyan-500 px-5 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
        >
          {busy ? "…" : "Upload"}
        </button>
      </form>
    </Card>
  );
}

function PolicyModal({
  doc,
  onClose,
  onSaved,
  notify,
}: {
  doc: DocSummary;
  onClose: () => void;
  onSaved: () => void;
  notify: (m: string) => void;
}) {
  const [policyText, setPolicyText] = useState(JSON.stringify(doc.access_policy ?? {}, null, 2));
  const [status, setStatus] = useState(doc.status);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setErr(null);
    let policy: Record<string, unknown>;
    try {
      policy = JSON.parse(policyText) as Record<string, unknown>;
    } catch {
      setErr("access_policy must be valid JSON");
      return;
    }
    setBusy(true);
    try {
      await api.updatePolicy(doc.id, { access_policy: policy, status });
      notify(`Policy saved for #${doc.id}`);
      onSaved();
    } catch (e) {
      if (e instanceof ApiError) setErr(e.message);
      else setErr("save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={`Policy — #${doc.id} ${doc.filename}`} onClose={onClose}>
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 block text-xs text-slate-400">access_policy (JSON)</span>
          <textarea
            value={policyText}
            onChange={(e) => setPolicyText(e.target.value)}
            rows={8}
            spellCheck={false}
            className="slim-scroll w-full rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-xs outline-none focus:border-cyan-500"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-slate-400">status</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          >
            <option value="active">active</option>
            <option value="revoked">revoked</option>
            <option value="archived">archived</option>
          </select>
        </label>
        {err && <div className="text-xs text-rose-300">{err}</div>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800">
            Cancel
          </button>
          <button
            onClick={() => void save()}
            disabled={busy}
            className="rounded-xl bg-cyan-500 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
          >
            {busy ? "…" : "Save"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

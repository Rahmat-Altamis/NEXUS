import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api, type ChatResponse, type Citation, type DocSummary, type HistoryItem } from "../lib/api";
import { useAuth } from "../lib/auth";
import { t } from "../lib/i18n";
import { Card, CardTitle, Empty, Modal, Spinner, StatusPill } from "../components/ui";

interface Turn {
  id: number;
  query: string;
  response: ChatResponse | null;
  error?: string;
}

const CITE_RE = /\[(\d+):(\d+)\]/g;

export default function Assistant() {
  const { lang } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [allowPii, setAllowPii] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [previewCite, setPreviewCite] = useState<Citation | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocSummary | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(1);

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await api.chatHistory(10));
    } catch {
      /* history is best-effort */
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    const id = idRef.current++;
    setTurns((prev) => [...prev, { id, query: message, response: null }]);
    setBusy(true);
    try {
      const res = await api.chat(message, lang, allowPii);
      setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, response: res } : t)));
      void loadHistory();
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, error: err instanceof Error ? err.message : "chat failed" } : t)),
      );
    } finally {
      setBusy(false);
    }
  }

  const openCitation = useCallback(async (cite: Citation) => {
    setPreviewCite(cite);
    setPreviewDoc(null);
    setPreviewError(null);
    setPreviewLoading(true);
    try {
      const doc = await api.getDocument(cite.doc_id, true);
      setPreviewDoc(doc);
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : "preview denied");
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_280px]">
      {/* Chat column */}
      <Card className="flex min-h-[60vh] flex-col">
        <CardTitle
          right={
            <label className="flex items-center gap-2 text-xs font-normal normal-case text-slate-400">
              <input
                type="checkbox"
                checked={allowPii}
                onChange={(e) => setAllowPii(e.target.checked)}
                className="h-3.5 w-3.5 accent-cyan-500"
              />
              allow PII (HR only)
            </label>
          }
        >
          {t(lang, "assistant")}
        </CardTitle>

        <div className="slim-scroll max-h-[55vh] flex-1 space-y-4 overflow-y-auto pr-1">
          {turns.length === 0 && (
            <Empty text={lang === "id" ? "Belum ada percakapan. Coba: “Berapa tunjangan transport?”" : "No conversation yet. Try: “What is the transport allowance?”"} />
          )}
          {turns.map((turn) => (
            <div key={turn.id} className="space-y-2">
              <div className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-md bg-cyan-500/15 px-4 py-2 text-sm ring-1 ring-cyan-500/30 ring-inset">
                {turn.query}
              </div>
              {turn.error ? (
                <div className="w-fit max-w-[90%] rounded-2xl rounded-bl-md border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-200">
                  {turn.error}
                </div>
              ) : turn.response ? (
                <AnswerBubble response={turn.response} onCite={(c) => void openCitation(c)} />
              ) : (
                <div className="w-fit rounded-2xl rounded-bl-md border border-slate-800 bg-slate-950 px-4 py-3">
                  <Spinner label="Reasoning…" />
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={send} className="mt-4 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t(lang, "askPlaceholder")}
            maxLength={4000}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm outline-none placeholder:text-slate-600 focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-bold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
          >
            {t(lang, "send")}
          </button>
        </form>
      </Card>

      {/* History column */}
      <Card className="h-fit">
        <CardTitle>{t(lang, "history")}</CardTitle>
        {history.length === 0 ? (
          <Empty text="—" />
        ) : (
          <ul className="slim-scroll max-h-[60vh] space-y-2 overflow-y-auto">
            {history.map((h) => (
              <li key={h.id} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <StatusPill status={h.status} />
                  {h.redacted && <span className="text-rose-300">[revoked]</span>}
                </div>
                <div className="truncate font-medium text-slate-300">{h.query}</div>
                <div className="mt-0.5 line-clamp-2 text-slate-500">
                  {h.redacted ? "[redacted: access revoked]" : h.answer}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Passage preview modal */}
      {previewCite && (
        <Modal
          title={previewDoc ? `#${previewDoc.id} ${previewDoc.filename} — chunk ${previewCite.chunk_idx}` : `Document #${previewCite.doc_id} — chunk ${previewCite.chunk_idx}`}
          onClose={() => setPreviewCite(null)}
        >
          {previewLoading ? (
            <Spinner label="Loading passage…" />
          ) : previewError ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {previewError}
            </div>
          ) : previewDoc ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="rounded bg-slate-800 px-2 py-0.5">{previewDoc.department}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5">v{previewDoc.version}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5">{previewDoc.effective_date || "no date"}</span>
              </div>
              <pre className="slim-scroll max-h-[50vh] overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs whitespace-pre-wrap text-slate-300">
                {previewDoc.text || "(no text)"}
              </pre>
            </div>
          ) : null}
        </Modal>
      )}
    </div>
  );
}

function AnswerBubble({
  response,
  onCite,
}: {
  response: ChatResponse;
  onCite: (c: Citation) => void;
}) {
  const refused = response.status === "refused";
  return (
    <div
      className={`w-fit max-w-[95%] space-y-2 rounded-2xl rounded-bl-md border px-4 py-3 text-sm ${
        refused ? "border-rose-500/30 bg-rose-500/5" : "border-slate-800 bg-slate-950"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={response.status} />
        {response.masked_pii && (
          <span className="inline-flex items-center rounded-full bg-violet-500/15 px-2.5 py-0.5 text-xs font-semibold text-violet-300 ring-1 ring-violet-500/40 ring-inset">
            PII masked
          </span>
        )}
        {response.status === "uncertain" && (
          <span className="text-xs text-slate-500">low confidence — verify with the document owner</span>
        )}
      </div>

      <div className="leading-relaxed whitespace-pre-wrap text-slate-200">
        {renderAnswer(response.answer, onCite)}
      </div>

      {response.warnings.length > 0 && (
        <div
          className={`rounded-xl border px-3 py-2 text-xs ${
            response.status === "conflict"
              ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
              : "border-slate-700 bg-slate-900 text-slate-400"
          }`}
        >
          <div className="mb-1 font-semibold tracking-wide uppercase opacity-80">warnings</div>
          <ul className="list-disc space-y-0.5 pl-4">
            {response.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <div className="mb-1 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">citations</div>
        {response.citations.length === 0 ? (
          <span className="text-xs text-slate-600">No citations</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {response.citations.map((c, i) => (
              <button
                key={`${c.doc_id}:${c.chunk_idx}:${i}`}
                onClick={() => onCite(c)}
                className="rounded-lg bg-cyan-500/10 px-2.5 py-1 font-mono text-xs font-semibold text-cyan-300 ring-1 ring-cyan-500/30 ring-inset hover:bg-cyan-500/25"
                title="Open passage preview"
              >
                [doc {c.doc_id} · chunk {c.chunk_idx}]
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** Render answer text with [doc:chunk] markers as clickable citation chips. */
function renderAnswer(answer: string, onCite: (c: Citation) => void): ReactNode[] {
  const parts: ReactNode[] = [];
  let last = 0;
  let key = 0;
  CITE_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = CITE_RE.exec(answer)) !== null) {
    if (m.index > last) parts.push(answer.slice(last, m.index));
    const doc_id = Number(m[1]);
    const chunk_idx = Number(m[2]);
    parts.push(
      <button key={key++} onClick={() => onCite({ doc_id, chunk_idx })} className="cite-mark" title={`Open doc ${doc_id} chunk ${chunk_idx}`}>
        [{doc_id}:{chunk_idx}]
      </button>,
    );
    last = m.index + m[0].length;
  }
  if (last < answer.length) parts.push(answer.slice(last));
  return parts;
}

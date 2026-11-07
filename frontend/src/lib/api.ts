/** Typed API client for the NEXUS backend. */

export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

const TOKEN_KEY = "nexus_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (init.body && typeof init.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
      else if (data.detail != null) detail = JSON.stringify(data.detail);
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/* ---------- Types (mirror backend shapes) ---------- */

export interface User {
  username: string;
  role: string;
  department: string;
}

export interface LoginResponse extends User {
  access_token: string;
  token_type: string;
}

export interface StatsSummary {
  users: number;
  documents: number;
  chunks: number;
  audit_events: number;
  security_events: number;
  chat_history: number;
}

export interface DocSummary {
  id: number;
  filename: string;
  source_type: string;
  department: string;
  author: string;
  effective_date: string;
  version: string;
  status: string;
  access_policy: Record<string, unknown>;
  text?: string;
}

export interface Citation {
  doc_id: number;
  chunk_idx: number;
}

export type ChatStatus = "ok" | "refused" | "uncertain" | "conflict";

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  status: ChatStatus | string;
  warnings: string[];
  masked_pii: boolean;
}

export interface HistoryItem {
  id: number;
  query: string;
  answer: string;
  citations: Citation[];
  status: string;
  redacted: boolean;
}

export interface SecEvent {
  id: number;
  ts: string;
  user: string;
  action: string;
  details: Record<string, unknown>;
}

/* ---------- Calls ---------- */

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),

  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<User>("/me"),

  stats: () => request<StatsSummary>("/stats/summary"),

  listDocuments: () => request<DocSummary[]>("/documents"),

  getDocument: (id: number, includeText = false) =>
    request<DocSummary>(`/documents/${id}?include_text=${includeText ? "true" : "false"}`),

  uploadDocument: async (
    file: File,
    meta: { department: string; author: string; effective_date: string },
  ): Promise<DocSummary> => {
    const form = new FormData();
    form.append("file", file);
    const params = new URLSearchParams({
      department: meta.department,
      author: meta.author,
      effective_date: meta.effective_date,
    });
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_URL}/documents/upload?${params}`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const data = (await res.json()) as { detail?: unknown };
        if (typeof data.detail === "string") detail = data.detail;
      } catch {
        /* keep default */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as DocSummary;
  },

  updatePolicy: (id: number, body: { access_policy?: Record<string, unknown>; status?: string }) =>
    request<DocSummary>(`/documents/${id}/policy`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteDocument: (id: number) =>
    request<{ deleted: number }>(`/documents/${id}`, { method: "DELETE" }),

  chat: (message: string, lang: string, allow_pii: boolean) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, lang, allow_pii }),
    }),

  chatHistory: (limit = 20) => request<HistoryItem[]>(`/chat/history?limit=${limit}`),

  securityEvents: (limit = 50) => request<SecEvent[]>(`/security/events?limit=${limit}`),

  auditEvents: (limit = 50) => request<SecEvent[]>(`/audit?limit=${limit}`),
};

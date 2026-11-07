/** Minimal bilingual strings (ID/EN) for the NEXUS demo UI. */

export type Lang = "id" | "en";

const STRINGS = {
  tagline: {
    id: "Asisten pengetahuan perusahaan yang aman",
    en: "Secure enterprise knowledge assistant",
  },
  dashboard: { id: "Dasbor", en: "Dashboard" },
  knowledge: { id: "Pengetahuan", en: "Knowledge" },
  assistant: { id: "Asisten AI", en: "AI Assistant" },
  security: { id: "Keamanan", en: "Security" },
  login: { id: "Masuk", en: "Sign in" },
  logout: { id: "Keluar", en: "Sign out" },
  username: { id: "Nama pengguna", en: "Username" },
  password: { id: "Kata sandi", en: "Password" },
  demoLogins: { id: "Login demo sekali klik", en: "One-click demo logins" },
  documents: { id: "Dokumen", en: "Documents" },
  upload: { id: "Unggah", en: "Upload" },
  askPlaceholder: {
    id: "Tanya tentang kebijakan, tunjangan, SOP…",
    en: "Ask about policies, benefits, SOPs…",
  },
  send: { id: "Kirim", en: "Send" },
  citations: { id: "Kutipan", en: "Citations" },
  noCitations: { id: "Tidak ada kutipan", en: "No citations" },
  warnings: { id: "Peringatan", en: "Warnings" },
  history: { id: "Riwayat", en: "History" },
  accessDenied: {
    id: "Akses ditolak — peran Anda tidak diizinkan.",
    en: "Access denied — your role is not permitted.",
  },
  backendTruth: {
    id: "UI menyembunyikan konten tanpa izin; backend adalah sumber kebenaran.",
    en: "The UI hides unauthorized content; the backend is the source of truth.",
  },
  piiShield: { id: "PII disamarkan", en: "PII masked" },
  revoked: { id: "Akses dicabut", en: "Access revoked" },
  recentQueries: { id: "Kueri terakhir", en: "Recent queries" },
  secEvents: { id: "Peristiwa keamanan", en: "Security events" },
  auditTrail: { id: "Jejak audit", en: "Audit trail" },
  ingestion: { id: "Status ingesti", en: "Ingestion status" },
} as const;

export type StringKey = keyof typeof STRINGS;

export function t(lang: Lang, key: StringKey): string {
  return STRINGS[key][lang];
}

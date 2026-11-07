"""Curated Indonesian <-> English synonym expansion for cross-lingual retrieval.

The default embedding is a monolingual hashed bag-of-words, so an English
query over Indonesian documents (and vice versa) scores ~0.0 even when
relevant accessible evidence exists. This module expands query-side tokens
with curated translations so either language retrieves evidence written in
either language.

Query-side only: stored vectors, chunking, and the authz-before-retrieval
boundary are unchanged. Every overlap gate still requires a genuine token
(or curated-translation) match, so hash-collision noise still fails and the
refused-vs-uncertain distinction keeps its meaning.

Only unambiguous domain terms are mapped. Deliberately NOT mapped: proper
nouns (Garuda, Komodo), Indonesian stopwords, and ambiguous words such as
"kata" (word) or "baru" (new/just) whose translations would add noise.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Each group is one concept in both languages (plus common inflections).
_GROUPS: list[frozenset[str]] = [
    frozenset(g)
    for g in [
        {"leave", "cuti"},
        {"annual", "tahunan"},
        {"year", "years", "yearly", "tahun"},
        {"month", "months", "monthly", "bulan", "bulanan"},
        {"week", "weeks", "weekly", "minggu", "mingguan"},
        {"day", "days", "daily", "hari", "harian"},
        {"policy", "policies", "kebijakan"},
        {"procedure", "procedures", "prosedur"},
        {"guide", "guides", "panduan"},
        {"manual", "manuals"},
        {"rule", "rules", "aturan"},
        {"regulation", "regulations", "regulasi"},
        {"compliance", "kepatuhan"},
        {"sop"},
        {"salary", "salaries", "gaji", "payroll", "payrolls"},
        {"wage", "wages", "upah"},
        {"compensation", "kompensasi"},
        {"remuneration", "remunerasi"},
        {"bonus", "bonuses"},
        {"overtime", "lembur"},
        {"allowance", "allowances", "tunjangan"},
        {"transport", "transportation", "transportasi"},
        {"travel", "perjalanan"},
        {"dinas"},
        {"employee", "employees", "karyawan"},
        {"staff"},
        {"company", "companies", "perusahaan"},
        {"office", "offices", "kantor"},
        {"finance", "keuangan"},
        {"financial"},
        {"expense", "expenses", "biaya"},
        {"claim", "claims", "klaim"},
        {"reimbursement", "reimbursements", "penggantian"},
        {"receipt", "receipts", "kwitansi"},
        {"budget", "budgets", "anggaran"},
        {"revenue", "revenues", "pendapatan"},
        {"profit", "profits", "laba"},
        {"loss", "losses", "rugi"},
        {"fund", "funds", "dana"},
        {"money", "uang"},
        {"wfh", "remote"},
        {"home", "rumah"},
        {"onboarding", "orientasi"},
        {"training", "trainings", "pelatihan"},
        {"mentor", "mentors"},
        {"announcement", "announcements", "pengumuman"},
        {"memo", "memos"},
        {"report", "reports", "laporan"},
        {"letter", "letters", "surat"},
        {"project", "projects", "proyek"},
        {"task", "tasks", "tugas"},
        {"meeting", "meetings", "rapat"},
        {"event", "events", "acara"},
        {"gathering"},
        {"holiday", "holidays", "libur"},
        {"sick", "sakit"},
        {"permit", "permits", "izin"},
        {"resignation", "resignations", "pengunduran"},
        {"contract", "contracts", "kontrak"},
        {"attendance", "kehadiran"},
        {"health", "kesehatan"},
        {"insurance", "asuransi"},
        {"performance", "kinerja"},
        {"review", "reviews", "penilaian"},
        {"team", "teams", "tim"},
        {"manager", "managers", "manajer"},
        {"director", "directors", "direktur"},
        {"supervisor", "supervisors", "atasan"},
        {"account", "accounts", "akun"},
        {"password", "passwords", "sandi"},
        {"security", "keamanan"},
        {"technology", "teknologi"},
        {"system", "systems", "sistem"},
        {"application", "applications", "aplikasi"},
        {"data"},
        {"archive", "archives", "arsip"},
        {"charter", "charters", "piagam"},
        {"directory", "directories", "direktori"},
        {"address", "addresses", "alamat"},
        {"phone", "phones", "telepon", "ponsel"},
        {"email", "emails", "surel"},
        {"birth", "lahir"},
        {"name", "names", "nama"},
        {"number", "numbers", "nomor"},
        {"calendar", "calendars", "kalender"},
        {"schedule", "schedules", "jadwal"},
        {"approval", "approvals", "persetujuan"},
        {"approved", "disetujui"},
        {"request", "requests", "permintaan", "pengajuan"},
        {"form", "forms", "formulir"},
    ]
]

_INDEX: dict[str, frozenset[str]] = {}
for _group in _GROUPS:
    for _term in _group:
        _INDEX.setdefault(_term, _group)


def expand_tokens(tokens: Iterable[str]) -> set[str]:
    """Return tokens plus their curated translations (all lowercase)."""
    out: set[str] = set()
    for tok in tokens:
        t = (tok or "").lower()
        if not t:
            continue
        out.add(t)
        out.update(_INDEX.get(t, ()))
    return out


def expand_query_text(query: str) -> str:
    """Return the query plus space-separated translation terms for embedding.

    The original text is kept verbatim (first) so monolingual scoring is
    unchanged; translations only add recall.
    """
    base = query or ""
    toks = _TOKEN_RE.findall(base.lower())
    extra = sorted(expand_tokens(toks) - set(toks))
    if not extra:
        return base
    return f"{base} {' '.join(extra)}"

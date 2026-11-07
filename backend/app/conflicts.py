"""Conflict detection: numeric/date contradictions across passages."""

from __future__ import annotations

import re
from collections import defaultdict

_RP_RE = re.compile(r"rp\s?([\d\.\,]+)", re.IGNORECASE)
_NUM_RE = re.compile(r"\b\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\b|\b\d+(?:[.,]\d+)?\b")
_DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
_TOKEN_RE = re.compile(r"[a-z]{3,}", re.IGNORECASE)

_STOPWORDS = frozenset({
    "the", "and", "for", "with", "dari", "yang", "dan", "ini", "itu",
    "adalah", "akan", "pada", "oleh", "untuk", "dalam", "sebagai",
    # Synthetic-corpus header boilerplate ("Nusantara Digital Group — dokumen
    # fiktif ..."): shared by every document, carries no topic signal.
    "nusantara", "digital", "group", "dokumen", "fiktif", "pengujian",
    "seluruh", "sintetis", "synthetic", "isi",
})

# Higher wins when newer; equal rank -> conflict must be reported.
AUTHORITY_RANK = {
    "announcement": 3,
    "pengumuman": 3,
    "sop": 2,
    "policy": 2,
    "kebijakan": 2,
    "memo": 1,
    "txt": 0,
    "md": 0,
    "csv": 0,
    "json": 0,
    "pdf": 1,
    "docx": 1,
}


def _authority_rank(authority: str) -> int:
    return AUTHORITY_RANK.get((authority or "").lower().strip(), 0)


def _amounts(text: str) -> list[str]:
    out = [f"Rp{m}" for m in _RP_RE.findall(text)]
    if out:
        return sorted(set(out))
    return sorted(set(_NUM_RE.findall(text)))


def _dates(text: str) -> list[str]:
    return sorted(set(_DATE_RE.findall(text)))


def _keywords(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)} - _STOPWORDS


def detect_conflicts(passages: list[dict]) -> list[dict]:
    """Group passages by topic keywords; flag differing amounts/dates.

    Returns [{topic, sources, explanation, resolved, winner}].
    Resolution: highest authority wins only if strictly highest AND newest
    effective_date; otherwise report conflict.
    """
    if len(passages) < 2:
        return []

    # Group: passages sharing >=2 *distinctive* keywords belong to one topic.
    # Keywords appearing in most of the result set (karyawan, hari, dokumen,
    # ...) carry no topic signal and would lump unrelated topics — e.g. a
    # gathering announcement "resolving" a leave-policy conflict — so they
    # are dropped before grouping. The cutoff keeps small result sets intact:
    # with 2 passages nothing is dropped.
    groups: list[list[int]] = []
    raw_kw = [_keywords(p.get("text", "")) for p in passages]
    df: dict[str, int] = {}
    for words in raw_kw:
        for w in words:
            df[w] = df.get(w, 0) + 1
    cutoff = max(2, len(passages) / 2)
    kw = [{w for w in words if df.get(w, 0) <= cutoff} for words in raw_kw]
    assigned = [-1] * len(passages)
    for i in range(len(passages)):
        if assigned[i] != -1:
            continue
        groups.append([i])
        assigned[i] = len(groups) - 1
        for j in range(i + 1, len(passages)):
            if assigned[j] == -1 and len(kw[i] & kw[j]) >= 2:
                groups[-1].append(j)
                assigned[j] = len(groups) - 1

    conflicts: list[dict] = []
    for g in groups:
        if len(g) < 2:
            continue
        vals: dict[str, list[int]] = defaultdict(list)
        for i in g:
            p = passages[i]
            facts = tuple(_amounts(p.get("text", "")) + _dates(p.get("text", "")))
            if facts:
                vals[str(facts)].append(i)
        if len(vals) < 2:
            continue
        topic_words = sorted(set.intersection(*[kw[i] for i in g]))[:5] or ["general"]
        topic = " ".join(topic_words)
        sources = [
            {
                "doc_id": passages[i].get("doc_id"),
                "filename": passages[i].get("filename"),
                "chunk_idx": passages[i].get("chunk_idx"),
                "effective_date": passages[i].get("effective_date", ""),
                "authority": passages[i].get("authority", ""),
            }
            for i in g
        ]
        # Resolution attempt: strictly-highest authority + newest date wins.
        ranked = sorted(
            g,
            key=lambda i: (_authority_rank(str(passages[i].get("authority", ""))), str(passages[i].get("effective_date", ""))),
            reverse=True,
        )
        top, second = ranked[0], ranked[1]
        top_rank = _authority_rank(str(passages[top].get("authority", "")))
        second_rank = _authority_rank(str(passages[second].get("authority", "")))
        top_date = str(passages[top].get("effective_date", ""))
        second_date = str(passages[second].get("effective_date", ""))
        if top_rank > second_rank and top_date >= second_date:
            conflicts.append({
                "topic": topic,
                "sources": sources,
                "explanation": (
                    f"Contradictory values {sorted(vals)} on '{topic}'; "
                    f"resolved in favor of {passages[top].get('filename')} "
                    f"(authority={passages[top].get('authority')}, date={top_date})."
                ),
                "resolved": True,
                "winner": sources[g.index(top)],
            })
        else:
            conflicts.append({
                "topic": topic,
                "sources": sources,
                "explanation": (
                    f"Conflict on '{topic}': differing values {sorted(vals)} across "
                    f"{len(g)} sources with equal/ambiguous authority; needs human review."
                ),
                "resolved": False,
                "winner": None,
            })
    return conflicts

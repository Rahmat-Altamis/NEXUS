"""Agent pipeline: classify -> authz -> retrieve -> scan -> validate ->
generate -> mask -> citation-check -> audit.

Refusal paths:
- unauthorized: generic "cannot answer" message, never confirms doc existence.
- unknown: explicit uncertainty + suggest the document owner.
- conflict: explain both sides with effective dates.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import conflicts as conflict_mod
from . import embeddings, injection, llm as llm_mod, pii as pii_mod, retrieval, synonyms, vectorstore
from .audit import log_query, log_security
from .authz import authorized_doc_ids, check_access_by_id
from .models import Document, User

_CITE_RE = re.compile(r"\[(\d+):(\d+)\]")
_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)

# Minimum cosine similarity for a passage to count as evidence. Calibrated:
# genuinely related query/passage pairs score ~0.3-0.6 with the hashed-BoW
# provider while unrelated pairs score ~0.0 (see phase-4 verification).
RELEVANCE_THRESHOLD = 0.05

# Step 1: sensitive-category keyword detection (ID + EN).
SENSITIVE_KEYWORDS: dict[str, set[str]] = {
    "salary": {
        "gaji", "salary", "payroll", "upah", "kompensasi", "compensation",
        "bonus", "tunjangan", "remunerasi", "remuneration", "take-home",
    },
    "finance": {
        "budget", "anggaran", "revenue", "pendapatan", "laba", "rugi",
        "profit", "keuangan", "financial", "arus kas", "cashflow",
        "cash flow", "audit keuangan", "laporan keuangan",
    },
    "pii": {
        "nik", "ktp", "alamat", "address", "telepon", "phone", "nomor hp",
        "email", "tanggal lahir", "date of birth", "tempat lahir", "npwp",
    },
}

# Roles allowed to receive unmasked PII, and only when explicitly requested.
PII_PRIVILEGED_ROLES = {"admin", "hr"}

# Function/question words ignored by the distinctive-term coverage check.
# Everything else the user names (names, entities, topic words) must appear
# — in either language — in at least one retrieved passage.
_COVERAGE_STOPWORDS = frozenset({
    "what", "when", "where", "which", "while", "who", "whom", "whose",
    "why", "how", "tell", "about", "above", "after", "again", "against",
    "all", "also", "among", "and", "any", "are", "because", "been",
    "before", "being", "between", "both", "but", "can", "cannot", "could",
    "describe", "did", "does", "doing", "down", "during", "each", "every",
    "explain", "find", "from", "further", "get", "give", "have", "having",
    "hello", "help", "here", "into", "is", "its", "just", "know", "like",
    "list", "more", "most", "need", "other", "over", "please", "provide",
    "same", "show", "some", "such", "summarise", "summarize", "than",
    "thank", "thanks", "that", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "under", "until", "very", "want",
    "was", "were", "will", "with", "would", "write", "your",
    "data", "info", "information", "informasi", "detail", "details", "rincian",
    "apa", "apakah", "ada", "adakah", "agar", "akan", "anda", "antara",
    "atas", "atau", "bagi", "bagaimana", "bagaimanakah", "banyak", "bawah",
    "belum", "berapa", "berikut", "berikan", "bersama", "bisa", "boleh", "bukan",
    "cara", "cari", "carikan", "cerita", "ceritakan", "contoh", "dalam",
    "dapat", "dari", "dengan", "dia", "dimana", "mana", "hal", "hanya",
    "harus", "hingga", "ingin", "jangan", "jelaskan", "jika",
    "juga", "kalau", "kami", "kapan", "karena", "katakan", "ke", "kepada",
    "kemudian", "kenapa", "kita", "kurang", "lagi", "lain",
    "lalu", "lebih", "lihat", "mau", "melalui", "mengenai", "mereka",
    "mengapa", "mohon", "namun", "oleh", "pada", "para", "perlu",
    "saja", "sampaikan", "sampai", "sangat", "saya", "sebutkan", "sejak",
    "selama", "semua", "seperti", "serta", "setiap", "siapa", "soal",
    "sudah", "supaya", "tampilkan", "tanpa", "tentang", "terhadap",
    "terkait", "tersebut", "tetapi", "tidak", "tolong", "tunjuk",
    "tunjukkan", "uraikan", "yang", "untuk",
})

_REFUSED_STATUS = "refused"
_UNCERTAIN_STATUS = "uncertain"
_CONFLICT_STATUS = "conflict"
_OK_STATUS = "ok"


def classify_query(query: str) -> dict:
    """Step 1: detect sensitive categories in the query text."""
    lowered = (query or "").lower()
    cats = sorted(
        cat for cat, words in SENSITIVE_KEYWORDS.items()
        if any(w in lowered for w in words)
    )
    return {"categories": cats, "sensitive": bool(cats)}


def _relevant_only(passages: list[dict], query: str) -> list[dict]:
    """Second relevance gate: keep passages sharing a content token (len>=4).

    Guards against hash-collision noise passing the cosine threshold with a
    single short-token match. Tokens are synonym-expanded so an English
    query genuinely matching Indonesian evidence (or vice versa) survives.
    """
    qtokens = synonyms.expand_tokens(_TOKEN_RE.findall((query or "").lower()))
    if not qtokens:
        return passages
    return [
        p for p in passages
        if qtokens & set(_TOKEN_RE.findall((p.get("text") or "").lower()))
    ]


def _uncovered_terms(passages: list[dict], query: str) -> list[str]:
    """Distinctive query terms appearing in no retrieved passage.

    Guards against partial-overlap misdirection: a question about "project
    Atlantis" shares "project"/"status" with Komodo/Garuda passages while
    its actual subject is absent. Every non-stopword query term (or its
    curated translation) must occur in at least one passage; otherwise the
    evidence does not answer the question asked.
    """
    qtokens = sorted(
        set(_TOKEN_RE.findall((query or "").lower())) - _COVERAGE_STOPWORDS
    )
    if not qtokens or not passages:
        return []
    psets = [
        set(_TOKEN_RE.findall((p.get("text") or "").lower())) for p in passages
    ]
    missing: list[str] = []
    for term in qtokens:
        accept = synonyms.expand_tokens([term])
        if not any(accept & words for words in psets):
            missing.append(term)
    return missing


def _has_unauthorized_evidence(db: Session, query: str) -> bool:
    """True when the corpus matches but the user may be locked out.

    Candidate hits are verified with the same content-token overlap gate the
    authorized retrieval path uses (_relevant_only): hashed-embedding cosine
    scores alone carry collision noise (up to ~0.27 on a 38-doc corpus, inside
    the genuine-match range), which would misclassify unknown topics as
    refused. Verification decrypts candidate chunks server-side and keeps only
    the boolean outcome — text is never returned, logged, or embedded in the
    response, so this check cannot leak restricted content.
    """
    try:
        all_ids = [d.id for d in db.scalars(select(Document)).all()]
        if not all_ids:
            return False
        qvec = embeddings.get_provider().embed(query)
        hits = vectorstore.search(db, qvec, all_ids, top_k=3, threshold=0.05)
        if not hits:
            return False
        qtokens = synonyms.expand_tokens(_TOKEN_RE.findall((query or "").lower()))
        if not qtokens:
            return True
        from .crypto import decrypt_bytes

        for chunk, _score in hits:
            try:
                text = decrypt_bytes(chunk.text_encrypted).decode("utf-8")
            except Exception:
                continue
            if qtokens & set(_TOKEN_RE.findall(text.lower())):
                return True
        return False
    except Exception:
        return False


def _check_citations(answer: str, passages: list[dict]) -> tuple[str, list[dict], int]:
    """Step 8: keep only citations mapping to a retrieved passage.

    Returns (cleaned_answer, valid_citations, dropped_count).
    """
    valid = {(p.get("doc_id"), p.get("chunk_idx", 0)) for p in passages}
    kept: list[dict] = []
    seen: set[tuple[Any, Any]] = set()

    def _sub(match: re.Match[str]) -> str:
        key = (int(match.group(1)), int(match.group(2)))
        if key in valid and key not in seen:
            seen.add(key)
            kept.append({"doc_id": key[0], "chunk_idx": key[1]})
            return match.group(0)
        if key in valid:
            return match.group(0)
        return ""

    dropped_before = len(_CITE_RE.findall(answer))
    cleaned = _CITE_RE.sub(_sub, answer)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, kept, max(0, dropped_before - len(_CITE_RE.findall(cleaned)))


def answer_query(
    db: Session,
    user: User,
    query: str,
    lang: str = "id",
    allow_pii: bool = False,
    top_k: int = 5,
) -> dict:
    """Run the full 9-step pipeline. Returns the chat response payload."""
    warnings: list[str] = []
    lk = "en" if (lang or "").lower().startswith("en") else "id"

    # 1) Classify.
    classification = classify_query(query)

    # 2) Authz scope.
    allowed_ids = authorized_doc_ids(user, db)

    # Query-level injection scan (logged, never executed).
    qscan = injection.scan_and_log(db, user.username, query, source="query")
    if qscan["flagged"]:
        warnings.append(
            "Prompt-injection patterns in your message were ignored."
            if lk == "en"
            else "Pola prompt-injection pada pesan Anda diabaikan."
        )
    effective_query = qscan["cleaned"]

    # 3) Retrieval (authorized docs only, relevance-gated).
    passages = retrieval.retrieve(
        db, user, effective_query, top_k=top_k, threshold=RELEVANCE_THRESHOLD
    )
    passages = _relevant_only(passages, effective_query)

    if not passages:
        # Refused (generic, no existence signal) vs uncertain (no evidence).
        if _has_unauthorized_evidence(db, effective_query):
            status = _REFUSED_STATUS
            answer = llm_mod.refusal_message(lk)
        else:
            status = _UNCERTAIN_STATUS
            answer = llm_mod.get_provider().generate(
                effective_query, [], lang=lk
            )["answer"]
        log_query(db, user.username, query, [], status,
                   authz_decision=f"allowed_docs={len(allowed_ids)}")
        return {
            "answer": answer,
            "citations": [],
            "status": status,
            "warnings": warnings,
            "masked_pii": False,
        }

    # 3b) Distinctive-term coverage: the named subject must actually occur
    # in the evidence. Partial word overlap with the wrong topic (project
    # Atlantis vs Proyek Komodo) is inadequate evidence -> uncertainty.
    uncovered = _uncovered_terms(passages, effective_query)
    if uncovered:
        status = _UNCERTAIN_STATUS
        answer = llm_mod.get_provider().generate(
            effective_query, [], lang=lk
        )["answer"]
        log_query(db, user.username, query, [], status,
                   authz_decision=(
                       f"allowed_docs={len(allowed_ids)} "
                       f"uncovered={','.join(uncovered[:5])}"
                   ))
        return {
            "answer": answer,
            "citations": [],
            "status": status,
            "warnings": warnings,
            "masked_pii": False,
        }

    # 4) Injection scan on retrieved passages.
    clean_passages: list[dict] = []
    for p in passages:
        found = injection.detect(p.get("text", "") or "")
        text = p.get("text", "") or ""
        if found["flagged"]:
            log_security(db, user.username, "prompt_injection_blocked", {
                "source": f"doc:{p.get('doc_id')}:chunk:{p.get('chunk_idx')}",
                "patterns": found["matches"],
                "snippet": text[:200],
            })
            text = injection.neutralize(text)
            warnings.append(
                f"Ignored injected instructions in document {p.get('doc_id')}."
                if lk == "en"
                else f"Instruksi injeksi pada dokumen {p.get('doc_id')} diabaikan."
            )
        clean_passages.append({**p, "text": text})

    # 5) Evidence validation + conflict detection.
    clean_passages = [p for p in clean_passages if (p.get("text") or "").strip()]
    if not clean_passages:
        status = _UNCERTAIN_STATUS
        answer = llm_mod.get_provider().generate(effective_query, [], lang=lk)["answer"]
        log_query(db, user.username, query, [], status, authz_decision="empty-after-scan")
        return {
            "answer": answer, "citations": [], "status": status,
            "warnings": warnings, "masked_pii": False,
        }
    detected = conflict_mod.detect_conflicts(clean_passages)
    unresolved = [c for c in detected if not c.get("resolved")]
    for c in detected:
        if c.get("resolved"):
            warnings.append(
                f"Resolved conflict on '{c['topic']}': {c['explanation']}"
                if lk == "en"
                else f"Konflik '{c['topic']}' diselesaikan: {c['explanation']}"
            )

    # PII decision (needed before generation): mask unless explicitly
    # authorized AND necessary. Privileged roles only.
    pii_authorized = bool(allow_pii) and user.role in PII_PRIVILEGED_ROLES

    # 6) Answer generation with citations. Passages are pre-masked on copies
    # so citations appended by the LLM can never be eaten by masking, and a
    # remote LLM never receives raw PII.
    gen_passages = clean_passages
    pre_masked = False
    if not pii_authorized:
        gen_passages = []
        for p in clean_passages:
            masked_text = pii_mod.mask(p.get("text", "") or "", authorized=False)
            pre_masked = pre_masked or (masked_text != (p.get("text", "") or ""))
            gen_passages.append({**p, "text": masked_text})
    provider = llm_mod.get_provider()
    generated = provider.generate(effective_query, gen_passages, lang=lk, conflicts=detected)
    answer = generated.get("answer", "")
    status = _OK_STATUS

    # Conflict path: explain both sides with dates.
    if unresolved:
        status = _CONFLICT_STATUS
        lines = [
            ("Conflicting information found:" if lk == "en"
             else "Ditemukan informasi yang bertentangan:"),
        ]
        for c in unresolved:
            for s in c.get("sources", []):
                lines.append(
                    f"- doc {s.get('doc_id')} ({s.get('filename')}, "
                    f"date={s.get('effective_date') or '-'}, "
                    f"authority={s.get('authority') or '-'}) "
                    f"[{s.get('doc_id')}:{s.get('chunk_idx')}]"
                )
            lines.append(f"  {c.get('explanation', '')}")
        answer = "\n".join(lines) + "\n\n" + answer
        warnings.append(
            "Sources conflict; both are shown with dates."
            if lk == "en"
            else "Sumber saling bertentangan; keduanya ditampilkan beserta tanggal."
        )

    # 7) PII masking safety net on the final answer (evidence was already
    # pre-masked; this catches PII in conflict headers/explanations).
    # Citations are shielded with newline-delimited placeholders first: the
    # address pattern ([^\n,;]) cannot span them, so citations survive.
    cites_found = _CITE_RE.findall(answer)
    shielded = answer
    for i, (d, c) in enumerate(cites_found):
        shielded = shielded.replace(f"[{d}:{c}]", f"\n\x00CITE{i}\x00\n", 1)
    masked_answer = pii_mod.mask(shielded, authorized=pii_authorized)
    for i, (d, c) in enumerate(cites_found):
        masked_answer = masked_answer.replace(
            f"\n\x00CITE{i}\x00\n", f"[{d}:{c}]", 1
        )
    masked_answer = masked_answer.replace("\x00", "")
    masked_pii = pre_masked or (masked_answer != answer)
    answer = masked_answer
    if masked_pii:
        warnings.append(
            "Personal data in the answer was masked."
            if lk == "en"
            else "Data pribadi pada jawaban telah disamarkan."
        )

    # 8) Citation integrity check.
    answer, citations, dropped = _check_citations(answer, clean_passages)
    if dropped:
        warnings.append(
            f"Dropped {dropped} invalid citation(s)."
            if lk == "en"
            else f"{dropped} kutipan tidak valid dibuang."
        )

    # 9) Audit log (query text PII-masked by the logger).
    retrieved_ids = sorted({p.get("doc_id") for p in clean_passages})
    log_query(
        db, user.username, query, retrieved_ids, status,
        authz_decision=(
            f"allowed_docs={len(allowed_ids)} "
            f"sensitive={','.join(classification['categories']) or 'none'}"
        ),
    )

    return {
        "answer": answer,
        "citations": citations,
        "status": status,
        "warnings": warnings,
        "masked_pii": masked_pii,
    }


def history_answer_visible(db: Session, user: User, citations: list[dict]) -> bool:
    """Re-check authz for history render: hide answers citing now-denied docs."""
    for c in citations or []:
        try:
            doc_id = int(c.get("doc_id"))
        except (TypeError, ValueError):
            continue
        allowed, _ = check_access_by_id(db, user, doc_id)
        if not allowed:
            return False
    return True

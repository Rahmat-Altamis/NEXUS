"""Permission-aware retrieval: embed -> authorized search -> dedupe -> cite."""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import embeddings, synonyms, vectorstore
from .authz import authorized_doc_ids
from .crypto import decrypt_bytes
from .models import Document, User


def retrieve(
    db: Session,
    user: User,
    query: str,
    top_k: int = 5,
    threshold: float = 0.0,
) -> list[dict]:
    """Return passages with citations; only docs the user may access."""
    allowed = authorized_doc_ids(user, db)
    if not allowed:
        return []
    qvec = embeddings.get_provider().embed(synonyms.expand_query_text(query))
    hits = vectorstore.search(db, qvec, allowed, top_k=top_k * 2, threshold=threshold)

    docs = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_(allowed))).all()}
    passages: list[dict] = []
    seen: set[str] = set()
    for chunk, score in hits:
        doc = docs.get(chunk.doc_id)
        if doc is None:
            continue
        try:
            text = decrypt_bytes(chunk.text_encrypted).decode("utf-8")
        except Exception:
            continue
        digest = hashlib.sha256(f"{chunk.doc_id}:{text}".encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        prov = chunk.provenance or {}
        passages.append({
            "text": text,
            "doc_id": chunk.doc_id,
            "filename": doc.filename,
            "chunk_idx": prov.get("chunk_idx", chunk.idx),
            "page": prov.get("page", 1),
            "score": round(float(score), 4),
            "effective_date": prov.get("effective_date", "") or doc.effective_date,
            "authority": prov.get("authority", "") or doc.source_type,
        })
        if len(passages) >= top_k:
            break
    return passages

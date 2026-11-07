"""Vector store: SQLite/Chunk-table backed, permission-first search.

search() filters by authorized_doc_ids BEFORE similarity ranking.
Raw vectors never leave this module (results carry chunk + score only).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import embeddings
from .models import Chunk


def add_chunks(
    db: Session,
    rows: list[dict],
    commit: bool = True,
) -> list[Chunk]:
    """Persist chunk rows: {doc_id, idx, text_encrypted, embedding, provenance}."""
    chunks: list[Chunk] = []
    for r in rows:
        c = Chunk(
            doc_id=r["doc_id"],
            idx=r.get("idx", 0),
            text_encrypted=r.get("text_encrypted", b""),
            embedding=r.get("embedding"),
            provenance=r.get("provenance", {}),
        )
        db.add(c)
        chunks.append(c)
    if commit:
        db.commit()
        for c in chunks:
            db.refresh(c)
    return chunks


def search(
    db: Session,
    query_vec: list[float],
    authorized_doc_ids: list[int] | set[int],
    top_k: int = 5,
    threshold: float = 0.0,
) -> list[tuple[Chunk, float]]:
    """Top-k chunks restricted to authorized docs, ranked by cosine similarity."""
    allowed = set(authorized_doc_ids or [])
    if not allowed:
        return []
    rows = db.scalars(select(Chunk).where(Chunk.doc_id.in_(allowed))).all()
    scored: list[tuple[Chunk, float]] = []
    for c in rows:
        vec = c.embedding or []
        score = embeddings.cosine_sim(query_vec, list(vec))
        if score >= threshold:
            scored.append((c, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[: max(0, top_k)]


def delete_chunks_for_doc(db: Session, doc_id: int, commit: bool = True) -> int:
    rows = db.scalars(select(Chunk).where(Chunk.doc_id == doc_id)).all()
    n = len(rows)
    for c in rows:
        db.delete(c)
    if commit:
        db.commit()
    return n

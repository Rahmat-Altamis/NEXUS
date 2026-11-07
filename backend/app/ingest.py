"""Ingestion: parse -> chunk -> encrypt -> embed -> index (real-time)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from . import chunking, embeddings, vectorstore
from .crypto import encrypt_bytes
from .models import Document
from .parsers import parse_bytes


def ingest_file(
    db: Session,
    filename: str,
    content: bytes,
    department: str = "general",
    author: str = "system",
    effective_date: str = "",
    version: str = "1.0",
    access_policy: dict | None = None,
    authority: str = "",
) -> Document:
    parsed = parse_bytes(filename, content)
    doc = Document(
        filename=filename,
        source_type=parsed.source_type,
        department=department,
        author=author,
        effective_date=effective_date or "",
        version=version,
        status="active",
        access_policy=access_policy or {},
        content_encrypted=encrypt_bytes(parsed.full_text.encode("utf-8")),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    provider = embeddings.get_provider()
    chunks = chunking.chunk_segments(
        parsed.segments, doc.id,
        effective_date=effective_date or "",
        authority=authority or parsed.source_type,
    )
    rows = []
    for i, c in enumerate(chunks):
        rows.append({
            "doc_id": doc.id,
            "idx": i,
            "text_encrypted": encrypt_bytes(c["text"].encode("utf-8")),
            "embedding": provider.embed(c["text"]),
            "provenance": c["provenance"],
        })
    vectorstore.add_chunks(db, rows)
    return doc


def reindex_document(db: Session, doc: Document) -> int:
    """Re-embed all chunks of a doc (e.g. after provider change). Returns count."""
    from sqlalchemy import select

    from .crypto import decrypt_bytes
    from .models import Chunk

    provider = embeddings.get_provider()
    chunks = db.scalars(select(Chunk).where(Chunk.doc_id == doc.id)).all()
    for c in chunks:
        try:
            text = decrypt_bytes(c.text_encrypted).decode("utf-8")
        except Exception:
            continue
        c.embedding = provider.embed(text)
    db.commit()
    return len(chunks)

"""Token-aware chunking with provenance."""

from __future__ import annotations

from .parsers import Segment

# ~500 tokens with overlap; 1 token ~= 0.75 words -> 375 words per chunk.
TARGET_TOKENS = 500
OVERLAP_TOKENS = 50
_WORDS_PER_TOKEN = 0.75


def _words_for(tokens: int) -> int:
    return max(10, int(tokens * _WORDS_PER_TOKEN))


def chunk_segments(
    segments: list[Segment],
    doc_id: int,
    effective_date: str = "",
    authority: str = "",
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[dict]:
    """Split segments into ~target_tokens word windows with overlap.

    Returns [{text, provenance: {doc_id, page, chunk_idx, effective_date,
    authority, line_start, line_end}}].
    """
    max_words = _words_for(target_tokens)
    overlap_words = _words_for(overlap_tokens)

    # Flatten to (word, page, line) tokens.
    tokens: list[tuple[str, int, int]] = []
    for seg in segments:
        for w in seg.text.split():
            tokens.append((w, seg.page, seg.line_start))

    chunks: list[dict] = []
    if not tokens:
        chunks.append({
            "text": "",
            "provenance": {
                "doc_id": doc_id, "page": 1, "chunk_idx": 0,
                "effective_date": effective_date, "authority": authority,
                "line_start": 1, "line_end": 1,
            },
        })
        return chunks

    idx = 0
    start = 0
    while start < len(tokens):
        end = min(start + max_words, len(tokens))
        window = tokens[start:end]
        text = " ".join(w for w, _, _ in window)
        chunks.append({
            "text": text,
            "provenance": {
                "doc_id": doc_id,
                "page": window[0][1],
                "chunk_idx": idx,
                "effective_date": effective_date,
                "authority": authority,
                "line_start": window[0][2],
                "line_end": window[-1][2],
            },
        })
        idx += 1
        if end >= len(tokens):
            break
        start = end - overlap_words
    return chunks


def chunk_text(
    text: str,
    doc_id: int,
    effective_date: str = "",
    authority: str = "",
    **kwargs,
) -> list[dict]:
    lines = text.splitlines() or [""]
    segs = [Segment(text=l, page=1, line_start=i + 1, line_end=i + 1) for i, l in enumerate(lines)]
    return chunk_segments(segs, doc_id, effective_date, authority, **kwargs)

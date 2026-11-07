"""Embeddings: provider abstraction + hashed TF-IDF-ish local default.

Raw vectors are internal only -- never expose them via the API.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class EmbeddingProvider(ABC):
    dim: int

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class LocalHashEmbedding(EmbeddingProvider):
    """Deterministic hashed bag-of-words with TF weighting + L2 norm.

    Token -> dim bucket via md5; weight = 1 + log(tf). Good enough for
    keyword-ish retrieval without external models.
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        counts: dict[int, int] = {}
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % self.dim
            counts[h] = counts.get(h, 0) + 1
        for h, c in counts.items():
            vec[h] = 1.0 + math.log(c)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class ChromaEmbedding(EmbeddingProvider):
    """Optional ChromaDB-backed embedding function passthrough.

    Uses chromadb's default embedding function when chromadb is installed.
    Falls back to LocalHashEmbedding when unavailable.
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self._fallback = LocalHashEmbedding(dim=dim)
        self._fn = None
        try:
            import chromadb.utils.embedding_functions as ef

            self._fn = ef.DefaultEmbeddingFunction()
        except Exception:
            self._fn = None

    def embed(self, text: str) -> list[float]:
        if self._fn is not None:
            try:
                vec = self._fn([text])[0]
                self.dim = len(vec)
                return list(vec)
            except Exception:
                pass
        return self._fallback.embed(text)


_provider: EmbeddingProvider | None = None


def get_provider() -> EmbeddingProvider:
    global _provider
    if _provider is not None:
        return _provider
    try:
        from .config import settings

        name = (settings.embedding_provider or "local").lower()
    except Exception:
        name = "local"
    if name == "chroma":
        _provider = ChromaEmbedding()
    else:
        _provider = LocalHashEmbedding()
    return _provider


def reset_provider() -> None:
    global _provider
    _provider = None

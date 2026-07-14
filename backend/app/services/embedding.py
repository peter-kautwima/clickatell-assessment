"""Local embeddings via sentence-transformers: one shared model instance
encodes text into unit-normalized 384-dimension vectors.

Model choice rationale: DECISIONS.md D2 (Embedding model).
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    # Cached so the ~90MB model loads once per process, not once per call.
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Encode texts into unit-normalized embedding vectors, preserving order."""
    if not texts:
        return []

    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()

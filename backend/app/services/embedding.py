"""Local embeddings via sentence-transformers (D2): one model instance shared
across calls, encoding chunk text into unit-normalized 384-dim vectors.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    # Cached so the ~90MB model loads once per process, not once per call.
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Encode texts into unit-normalized embedding vectors, preserving order."""
    if not texts:
        return []

    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()

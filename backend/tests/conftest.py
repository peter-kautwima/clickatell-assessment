import numpy as np
import pytest
from app.services import embedding as embedding_module

EMBEDDING_DIM = 384


class _FakeModel:
    """Stands in for SentenceTransformer: deterministic, no download, no torch."""

    def __init__(self) -> None:
        self.calls: list = []

    def encode(self, texts, normalize_embeddings: bool = True):
        self.calls.append(list(texts))
        vectors = np.zeros((len(texts), EMBEDDING_DIM), dtype=float)
        for row, text in enumerate(texts):
            # Deterministic fingerprint so identical input -> identical output,
            # and different input -> different output, without hashing.
            vectors[row, 0] = len(text) + 1
            vectors[row, 1] = sum(ord(c) for c in text) % 97 + 1
        if normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors = vectors / norms
        return vectors


@pytest.fixture(autouse=True)
def mock_embedding_model(monkeypatch):
    """Never let a test load the real ~90MB sentence-transformers model."""
    fake = _FakeModel()
    monkeypatch.setattr(embedding_module, "_get_model", lambda: fake)
    return fake


@pytest.fixture
def sample_text() -> str:
    return "This is a sample document text."

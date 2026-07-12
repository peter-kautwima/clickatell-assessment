import numpy as np
import pytest
from app.config import settings
from app.main import app
from app.services import embedding as embedding_module
from app.storage.memory import get_store
from fastapi.testclient import TestClient

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


@pytest.fixture(autouse=True)
def keyless_settings(monkeypatch):
    """Pin the LLM toggle to keyless. The settings singleton is built at import
    time, so a real ANTHROPIC_API_KEY in .env would silently flip the whole
    suite onto the live path (DECISIONS.md D4 — LLM integration & prompt
    design). Live-path tests set a fake key explicitly.
    """
    monkeypatch.setattr(settings, "anthropic_api_key", None)


@pytest.fixture(autouse=True)
def reset_store():
    """Empty the process-wide store after each test, via its PUBLIC interface
    only — no reaching into private matrix/dict internals.
    """
    yield
    store = get_store()
    for document in store.list():
        store.delete(document.id)


@pytest.fixture
def client(mock_embedding_model) -> TestClient:
    """App client with lifespan running — warm-up hits the mocked model."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_text() -> str:
    return "This is a sample document text."

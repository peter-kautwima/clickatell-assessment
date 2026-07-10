import numpy as np
from app.services.embedding import embed_texts


def test_empty_input_returns_no_vectors_without_calling_model(mock_embedding_model):
    assert embed_texts([]) == []
    assert mock_embedding_model.calls == []


def test_embed_texts_preserves_order_and_dimension(mock_embedding_model):
    vectors = embed_texts(["alpha", "beta", "gamma"])

    assert len(vectors) == 3
    assert all(len(vector) == 384 for vector in vectors)
    assert mock_embedding_model.calls == [["alpha", "beta", "gamma"]]


def test_embed_texts_is_deterministic_for_the_same_input():
    first = embed_texts(["same text"])
    second = embed_texts(["same text"])

    assert first == second


def test_embed_texts_returns_unit_normalized_vectors():
    vectors = embed_texts(["some chunk of text"])

    norm = np.linalg.norm(vectors[0])
    assert abs(norm - 1.0) < 1e-9

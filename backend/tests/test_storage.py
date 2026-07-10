from datetime import UTC

import pytest
from app.errors import DocumentNotFoundError
from app.storage.memory import InMemoryVectorStore


@pytest.fixture
def store() -> InMemoryVectorStore:
    # Fresh instance per test — never the module-level singleton, so these
    # unit tests stay independent of the app's shared state.
    return InMemoryVectorStore()


def test_add_returns_record_with_stamped_metadata(store):
    doc = store.add("doc-1", "My title", ["chunk a", "chunk b"], [[1.0], [0.0]])

    assert doc.id == "doc-1"
    assert doc.title == "My title"
    assert doc.chunk_count == 2
    assert doc.chunks == ["chunk a", "chunk b"]
    # created_at is stamped by the store itself, timezone-aware UTC.
    assert doc.created_at.tzinfo == UTC


def test_list_returns_documents_in_upload_order(store):
    store.add("doc-1", "First", ["a"], [[1.0]])
    store.add("doc-2", "Second", ["b"], [[0.5]])

    listed = store.list()

    assert [d.id for d in listed] == ["doc-1", "doc-2"]


def test_get_returns_the_same_record_add_created(store):
    added = store.add("doc-1", "Title", ["a", "b"], [[1.0], [0.0]])

    assert store.get("doc-1") is added


def test_get_unknown_id_raises(store):
    with pytest.raises(DocumentNotFoundError):
        store.get("no-such-id")


def test_delete_removes_document_and_its_vectors(store):
    store.add("doc-1", "Title", ["a"], [[1.0, 0.0]])

    store.delete("doc-1")

    assert store.list() == []
    with pytest.raises(DocumentNotFoundError):
        store.get("doc-1")
    assert store.search([1.0, 0.0], k=5) == []


def test_delete_unknown_id_raises(store):
    with pytest.raises(DocumentNotFoundError):
        store.delete("no-such-id")


def test_delete_only_removes_that_documents_rows(store):
    store.add("doc-1", "Keep", ["kept chunk"], [[1.0, 0.0]])
    store.add("doc-2", "Drop", ["dropped chunk"], [[0.0, 1.0]])

    store.delete("doc-2")

    results = store.search([1.0, 1.0], k=5)
    assert [(chunk, doc_id) for chunk, doc_id, _ in results] == [
        ("kept chunk", "doc-1")
    ]


def test_search_scores_are_exact_dot_products(store):
    # Two axis-aligned unit vectors against a (0.6, 0.8) unit query: the
    # dot products are exactly 0.6 and 0.8 — cosine similarity with no
    # normalization step, because everything is already unit length (D3).
    store.add("doc-1", "Title", ["x chunk", "y chunk"], [[1.0, 0.0], [0.0, 1.0]])

    results = store.search([0.6, 0.8], k=2)

    assert [(chunk, doc_id) for chunk, doc_id, _ in results] == [
        ("y chunk", "doc-1"),
        ("x chunk", "doc-1"),
    ]
    assert results[0][2] == pytest.approx(0.8)
    assert results[1][2] == pytest.approx(0.6)


def test_search_returns_top_k_best_first_across_documents(store):
    store.add("doc-1", "One", ["far"], [[-1.0, 0.0]])
    store.add("doc-2", "Two", ["near"], [[1.0, 0.0]])
    store.add("doc-3", "Three", ["middle"], [[0.7071, 0.7071]])

    results = store.search([1.0, 0.0], k=2)

    assert [chunk for chunk, _, _ in results] == ["near", "middle"]
    scores = [score for _, _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_search_k_larger_than_row_count_returns_everything(store):
    store.add("doc-1", "Title", ["only chunk"], [[1.0]])

    assert len(store.search([1.0], k=100)) == 1


def test_search_on_empty_store_returns_empty(store):
    assert store.search([1.0, 0.0], k=3) == []


def test_search_with_nonpositive_k_returns_empty(store):
    store.add("doc-1", "Title", ["a"], [[1.0]])

    assert store.search([1.0], k=0) == []

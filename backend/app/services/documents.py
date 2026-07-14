"""Document ingestion and the get/list/delete bookkeeping the four /documents
routes delegate to — one function per endpoint.
"""

from __future__ import annotations

from uuid import uuid4

from ..errors import EmptyDocumentError
from ..storage.base import StoredDocument, VectorStore
from .chunking import chunk_text
from .embedding import embed_texts


def ingest_document(title: str, content: str, store: VectorStore) -> StoredDocument:
    """The POST /documents pipeline: chunk -> embed -> store.

    Raises EmptyDocumentError when chunking yields nothing — one check that
    covers both empty and whitespace-only content (the semantic 400 in
    DECISIONS.md D5).
    """
    chunks = chunk_text(content)
    if not chunks:
        raise EmptyDocumentError()
    vectors = embed_texts(chunks)
    # uuid4 hex: collision-free ids with no counter to synchronise. The global
    # counter in the Part 2 module was the anti-pattern here.
    return store.add(uuid4().hex, title, chunks, vectors)


def get_document(doc_id: str, store: VectorStore) -> StoredDocument:
    """Single-document lookup; DocumentNotFoundError propagates from the store."""
    return store.get(doc_id)


def list_documents(store: VectorStore) -> list[StoredDocument]:
    """All stored documents in upload order."""
    return store.list()


def delete_document(doc_id: str, store: VectorStore) -> None:
    """Remove a document and its data; DocumentNotFoundError propagates."""
    store.delete(doc_id)

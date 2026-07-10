"""Document ingestion and bookkeeping: the service layer the four /documents
routes delegate to, one function per endpoint (DECISIONS.md §1 — every
endpoint validates, calls ONE service function, returns a schema).
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
    covers both empty and whitespace-only content (DECISIONS.md D5 — Error
    handling: semantic 400, distinct from Pydantic's shape-level 422).
    """
    chunks = chunk_text(content)
    if not chunks:
        raise EmptyDocumentError()
    vectors = embed_texts(chunks)
    # uuid4 hex: collision-free ids without a counter to synchronize
    # (the Part 2 review module's global counter is the anti-pattern here).
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

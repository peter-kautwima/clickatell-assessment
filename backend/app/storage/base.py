"""The VectorStore interface, per DECISIONS.md D3 (Vector storage & search):
the seam that lets the in-memory implementation swap for pgvector/ChromaDB
with no other file changing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StoredDocument:
    """One document as storage sees it — deliberately a plain dataclass, not
    the Pydantic schema, so the storage layer stays independent of the HTTP
    contract (routes map this to models/schemas.py types).
    """

    id: str
    title: str
    uploaded_at: datetime
    chunks: list[str]

    @property
    def chunk_count(self) -> int:
        """Derived, never stored — cannot drift out of sync with chunks."""
        return len(self.chunks)


class VectorStore(ABC):
    """DECISIONS.md D3 interface (plus its addendum: title on add(), get()
    as a fifth method, uploaded_at stamped by the store at add time).
    """

    @abstractmethod
    def add(
        self,
        doc_id: str,
        title: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> StoredDocument:
        """Store a document's chunks and their (already unit-normalized,
        per DECISIONS.md D2 — Embedding model) vectors; return its record.
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, query_vector: list[float], k: int) -> list[tuple[str, str, float]]:
        """Top-k most similar chunks across all documents, best first, as
        (chunk_text, doc_id, score) tuples.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, doc_id: str) -> StoredDocument:
        """Return one document's record; raise DocumentNotFoundError if absent."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove a document and its vectors; raise DocumentNotFoundError if absent."""
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[StoredDocument]:
        """All stored documents, in upload order."""
        raise NotImplementedError

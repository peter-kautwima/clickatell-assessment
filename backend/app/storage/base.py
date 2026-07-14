"""The VectorStore interface: the seam that lets the in-memory implementation
swap for pgvector or another store with no other file changing.

Storage and similarity-search rationale: DECISIONS.md D3
(Vector storage & search).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StoredDocument:
    """One document as storage sees it — a plain dataclass, not the Pydantic
    schema, so the storage layer stays independent of the HTTP contract.
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
    """The storage interface the rest of the app depends on: add() takes the
    document title and stamps uploaded_at, get() does the single-document
    lookup, and search() ranks chunks.
    """

    @abstractmethod
    def add(
        self,
        doc_id: str,
        title: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> StoredDocument:
        """Store a document's chunks and their (already unit-normalized)
        vectors; return its record.
        """

    @abstractmethod
    def search(self, query_vector: list[float], k: int) -> list[tuple[str, str, float]]:
        """Top-k most similar chunks across all documents, best first, as
        (chunk_text, doc_id, score) tuples.
        """

    @abstractmethod
    def get(self, doc_id: str) -> StoredDocument:
        """Return one document's record; raise DocumentNotFoundError if absent."""

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove a document and its vectors; raise DocumentNotFoundError if absent."""

    @abstractmethod
    def list(self) -> list[StoredDocument]:
        """All stored documents, in upload order."""

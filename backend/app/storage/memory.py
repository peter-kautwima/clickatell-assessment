"""In-memory VectorStore, per DECISIONS.md D3 (Vector storage & search): one
numpy matrix of unit vectors plus a parallel per-row metadata list, so cosine
similarity over every chunk is a single matrix @ query dot product.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from ..errors import DocumentNotFoundError
from .base import StoredDocument, VectorStore


class InMemoryVectorStore(VectorStore):
    """Exact (brute-force) search — correct and quick at assessment scale,
    swapped for an ANN-indexed store in production (DECISIONS.md §4.1).
    """

    def __init__(self) -> None:
        """Start empty: no vector rows, no documents."""
        # Vectors arrive already unit-normalized from embed_texts()
        # (DECISIONS.md D2 — Embedding model) and are stored AS-IS, never
        # re-normalized — that is what makes the raw dot product equal
        # cosine similarity at search time (DECISIONS.md D3).
        self._matrix: np.ndarray | None = None
        # One (chunk_text, doc_id) entry per matrix row, same order.
        self._rows: list[tuple[str, str]] = []
        self._documents: dict[str, StoredDocument] = {}

    def add(
        self,
        doc_id: str,
        title: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> StoredDocument:
        """Append the document's rows to the matrix and record its metadata.

        Assumes chunks is non-empty — the ingestion service raises
        EmptyDocumentError before ever reaching storage (DECISIONS.md D5 —
        Error handling).
        """
        document = StoredDocument(
            id=doc_id,
            title=title,
            uploaded_at=datetime.now(UTC),
            chunks=list(chunks),
        )
        new_rows = np.asarray(vectors, dtype=float)
        if self._matrix is None:
            self._matrix = new_rows
        else:
            self._matrix = np.vstack([self._matrix, new_rows])
        self._rows.extend((chunk, doc_id) for chunk in chunks)
        self._documents[doc_id] = document
        return document

    def search(self, query_vector: list[float], k: int) -> list[tuple[str, str, float]]:
        """Score every chunk in one dot product; return the top k, best first."""
        if self._matrix is None or k <= 0:
            return []
        scores = self._matrix @ np.asarray(query_vector, dtype=float)
        # argsort is ascending; reverse for best-first, then cut to k
        # (numpy slicing tolerates k > row count by returning everything).
        top_indices = np.argsort(scores)[::-1][:k]
        return [
            (self._rows[i][0], self._rows[i][1], float(scores[i])) for i in top_indices
        ]

    def get(self, doc_id: str) -> StoredDocument:
        """Return one document's record; raise DocumentNotFoundError if absent."""
        try:
            return self._documents[doc_id]
        except KeyError:
            raise DocumentNotFoundError(doc_id) from None

    def delete(self, doc_id: str) -> None:
        """Drop the document's metadata and mask its rows out of the matrix."""
        if doc_id not in self._documents:
            raise DocumentNotFoundError(doc_id)
        keep = [
            i for i, (_, row_doc_id) in enumerate(self._rows) if row_doc_id != doc_id
        ]
        self._matrix = self._matrix[keep] if keep else None
        self._rows = [self._rows[i] for i in keep]
        del self._documents[doc_id]

    def list(self) -> list[StoredDocument]:
        """All documents in upload order (dict preserves insertion order)."""
        return list(self._documents.values())


# Process-wide instance: the store is the service's only stateful component
# (DECISIONS.md §1), so exactly one lives for the app's lifetime.
_store = InMemoryVectorStore()


def get_store() -> VectorStore:
    """FastAPI dependency returning the shared store instance."""
    return _store

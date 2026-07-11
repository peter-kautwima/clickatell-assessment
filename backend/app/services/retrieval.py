"""Question retrieval service: embed once, then delegate ranking to VectorStore.
It preserves DECISIONS.md D3 (Vector storage & search): no score math or
normalization here, only the two-call retrieval pipeline.
"""

from __future__ import annotations

from ..errors import EmptyQuestionError
from ..storage.base import VectorStore
from .embedding import embed_texts

# Mirrored by QueryRequest.k's schema default in models/schemas.py, which also
# owns the HTTP-facing 1–10 bounds; this one serves direct callers that skip
# the schema, e.g. /ask calling retrieve_similar() — DECISIONS.md D3 (Vector
# storage & search), query endpoint choices.
DEFAULT_QUERY_K = 5


def retrieve_similar(
    question: str, store: VectorStore, k: int = DEFAULT_QUERY_K
) -> list[tuple[str, str, float]]:
    """Return top-k chunks for a non-empty natural-language question."""
    cleaned_question = question.strip()
    if not cleaned_question:
        raise EmptyQuestionError()

    query_vector = embed_texts([cleaned_question])[0]
    return store.search(query_vector, k)

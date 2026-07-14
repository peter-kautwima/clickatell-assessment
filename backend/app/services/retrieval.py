"""Question retrieval: embed the question once, then delegate ranking to the
VectorStore. No score maths or normalization lives here.

Retrieval and the k default: DECISIONS.md D3 (Vector storage & search).
"""

from __future__ import annotations

from ..errors import EmptyQuestionError
from ..storage.base import VectorStore
from .embedding import embed_texts

# Mirrored by QueryRequest.k's schema default, which also owns the 1-10 HTTP
# bounds; this default serves direct callers that skip the schema (e.g. /ask).
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

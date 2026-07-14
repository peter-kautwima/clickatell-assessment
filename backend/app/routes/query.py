"""The /query and /ask endpoints — thin HTTP translation over the services."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..models.schemas import (
    AskRequest,
    AskResponse,
    ErrorResponse,
    QueryRequest,
    QueryResponse,
    QueryResult,
)
from ..services import answering as answering_service
from ..services import retrieval as retrieval_service
from ..storage.base import VectorStore
from ..storage.memory import get_store

router = APIRouter()

StoreDep = Annotated[VectorStore, Depends(get_store)]

_EMPTY_QUESTION = {
    400: {"model": ErrorResponse, "description": "Empty or whitespace-only question"}
}
# /ask can also fail upstream at the LLM — surface the 502 in the docs too.
_ASK_ERRORS = {
    **_EMPTY_QUESTION,
    502: {"model": ErrorResponse, "description": "Upstream LLM call failed"},
}


@router.post("/query", responses=_EMPTY_QUESTION)
def query_documents(payload: QueryRequest, store: StoreDep) -> QueryResponse:
    """Embed the question and return the highest-scoring chunks across documents."""
    matches = retrieval_service.retrieve_similar(payload.question, store, payload.k)
    return QueryResponse(
        results=[
            QueryResult(document_id=doc_id, chunk=chunk, score=score)
            for chunk, doc_id, score in matches
        ]
    )


# The one async endpoint: the I/O-bound LLM call is awaited on the event loop,
# while the CPU-bound embedding step inside answer_question runs in the thread
# pool (DECISIONS.md D6).
@router.post("/ask", responses=_ASK_ERRORS)
async def ask_question(payload: AskRequest, store: StoreDep) -> AskResponse:
    """Answer a question grounded in retrieved chunks; return answer + sources."""
    answer, sources = await answering_service.answer_question(
        payload.question, store, payload.k
    )
    return AskResponse(
        answer=answer,
        sources=[
            QueryResult(document_id=doc_id, chunk=chunk, score=score)
            for chunk, doc_id, score in sources
        ],
    )

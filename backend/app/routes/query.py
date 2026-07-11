"""The /query and /ask endpoints — thin HTTP translation over
services/retrieval.py and services/answering.py (DECISIONS.md §3 assigns
both endpoints to this file).
"""

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


@router.post("/ask", responses=_ASK_ERRORS)
async def ask_question(payload: AskRequest, store: StoreDep) -> AskResponse:
    """Answer a question grounded in retrieved chunks, returning the answer
    plus the sources it used.

    The one async endpoint: the LLM call is I/O-bound and awaited on the
    event loop (CLAUDE.md rule 9 — concurrency); the CPU-bound embed step is
    dispatched to the threadpool inside the service.
    """
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

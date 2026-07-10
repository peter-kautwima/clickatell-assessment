"""The /query endpoint — thin HTTP translation over services/retrieval.py."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..models.schemas import ErrorResponse, QueryRequest, QueryResponse, QueryResult
from ..services import retrieval as retrieval_service
from ..storage.base import VectorStore
from ..storage.memory import get_store

router = APIRouter()

StoreDep = Annotated[VectorStore, Depends(get_store)]

_EMPTY_QUESTION = {
    400: {"model": ErrorResponse, "description": "Empty or whitespace-only question"}
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

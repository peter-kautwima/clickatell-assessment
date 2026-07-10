"""The four /documents endpoints — thin HTTP translation over
services/documents.py, zero business logic (DECISIONS.md §1 System
Overview / §3 Module Map & Responsibilities).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..models.schemas import (
    DocumentCreate,
    DocumentDetail,
    DocumentListResponse,
    DocumentMeta,
    ErrorResponse,
)
from ..services import documents as documents_service
from ..storage.base import StoredDocument, VectorStore
from ..storage.memory import get_store

router = APIRouter()

# Annotated dependency (not a `= Depends(...)` default) so ruff's B008
# function-call-in-default check stays clean without an exemption.
StoreDep = Annotated[VectorStore, Depends(get_store)]

# Declared per-route so the auto-docs at /docs show the D5 error contract,
# not just the happy path (ASSESSMENT.md eval: useful documentation).
_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Unknown document id"}}
_EMPTY_CONTENT = {
    400: {"model": ErrorResponse, "description": "Empty or whitespace-only content"}
}


def _to_meta(document: StoredDocument) -> DocumentMeta:
    """Map storage's dataclass to the HTTP metadata schema."""
    return DocumentMeta(
        id=document.id,
        title=document.title,
        chunk_count=document.chunk_count,
        uploaded_at=document.uploaded_at,
    )


# All four endpoints are plain `def`, not `async def`: upload's embedding is
# CPU-bound and the rest are pure in-memory work, so FastAPI's threadpool is
# the right home (CLAUDE.md rule 9 — concurrency / DECISIONS.md D6).
@router.post(
    "/documents",
    status_code=201,
    responses=_EMPTY_CONTENT,
)
def upload_document(payload: DocumentCreate, store: StoreDep) -> DocumentMeta:
    """Chunk, embed, and store a pasted plain-text/markdown document."""
    document = documents_service.ingest_document(payload.title, payload.content, store)
    return _to_meta(document)


@router.get("/documents")
def list_documents(store: StoreDep) -> DocumentListResponse:
    """List every document's id, title, chunk count, and upload date."""
    documents = documents_service.list_documents(store)
    return DocumentListResponse(documents=[_to_meta(d) for d in documents])


# Path param is named `id` (shadowing the builtin inside these two tiny
# functions) so /docs renders exactly /documents/{id} — the literal path
# template in ASSESSMENT.md's endpoint table.
@router.get("/documents/{id}", responses=_NOT_FOUND)
def get_document(id: str, store: StoreDep) -> DocumentDetail:
    """One document's metadata plus its stored chunks."""
    document = documents_service.get_document(id, store)
    return DocumentDetail(
        id=document.id,
        title=document.title,
        chunk_count=document.chunk_count,
        uploaded_at=document.uploaded_at,
        chunks=document.chunks,
    )


@router.delete("/documents/{id}", status_code=204, responses=_NOT_FOUND)
def delete_document(id: str, store: StoreDep) -> None:
    """Remove a document and its vectors; 204 with no body on success."""
    documents_service.delete_document(id, store)

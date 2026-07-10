"""Every Pydantic request/response contract in one place, per ASSESSMENT.md
tech req 5 (Pydantic models for ALL bodies — error responses included).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """POST /documents request body: a pasted plain-text/markdown document."""

    title: str = Field(min_length=1)
    # content is deliberately NOT length-constrained here: empty/whitespace-only
    # text is a semantic error owned by the service (HTTP 400 via
    # EmptyDocumentError), not a schema-shape error (HTTP 422) — DECISIONS.md
    # D5 (Error handling) separates those two cases.
    content: str


class DocumentMeta(BaseModel):
    """One document's metadata — the exact GET /documents field list the
    brief requires: id, title, chunk count, upload date.
    """

    id: str
    title: str
    chunk_count: int
    # "uploaded_at" over the more conventional "created_at": our own
    # clearer-naming choice (the brief says "upload date" in prose but
    # never dictates a JSON key).
    uploaded_at: datetime


class DocumentDetail(DocumentMeta):
    """GET /documents/{id} response: metadata plus the stored chunk texts."""

    chunks: list[str]


class DocumentListResponse(BaseModel):
    """GET /documents response — wrapped in an object rather than a bare
    array so pagination fields can be added without breaking clients
    (DECISIONS.md §4.1 production readiness).
    """

    documents: list[DocumentMeta]


class ErrorDetail(BaseModel):
    """Machine-readable code + human-readable message for one error."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """The single JSON error shape every handler returns, per DECISIONS.md D5
    (Error handling): {"error": {"code", "message"}}.
    """

    error: ErrorDetail

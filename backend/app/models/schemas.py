"""Every Pydantic request and response contract in one place, error responses
included.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """POST /documents request body: a pasted plain-text/markdown document."""

    title: str = Field(min_length=1)
    # content is not length-constrained here: empty/whitespace-only text is a
    # semantic error the service returns as a 400, not a schema-shape 422
    # (DECISIONS.md D5).
    content: str


class DocumentMeta(BaseModel):
    """One document's metadata: id, title, chunk count, and upload date."""

    id: str
    title: str
    chunk_count: int
    # uploaded_at rather than created_at — a clearer name; the brief says
    # "upload date" in prose but doesn't dictate the JSON key.
    uploaded_at: datetime


class DocumentDetail(DocumentMeta):
    """GET /documents/{id} response: metadata plus the stored chunk texts."""

    chunks: list[str]


class DocumentListResponse(BaseModel):
    """GET /documents response.

    Wrapped in an object rather than a bare array so pagination fields can be
    added later without breaking clients (DECISIONS.md D3).
    """

    documents: list[DocumentMeta]


class QueryRequest(BaseModel):
    """POST /query request body: question plus bounded result count."""

    # Not length-constrained here (same as DocumentCreate.content): an
    # empty/whitespace question is a semantic 400, not a schema-shape 422.
    question: str
    # Default mirrors retrieval.DEFAULT_QUERY_K; the 1-10 bounds live only here,
    # at the HTTP edge (DECISIONS.md D3).
    k: int = Field(default=5, ge=1, le=10)


class QueryResult(BaseModel):
    """One retrieved source chunk and its cosine-similarity score."""

    document_id: str
    chunk: str
    score: float


class QueryResponse(BaseModel):
    """POST /query response: ranked source chunks, empty when nothing is stored."""

    results: list[QueryResult] = Field(default_factory=list)


class AskRequest(BaseModel):
    """POST /ask request body: question plus bounded retrieval count."""

    # Not length-constrained here (same as QueryRequest.question): an
    # empty/whitespace question is a semantic 400, not a schema-shape 422.
    question: str
    # Same 1-10 bounds and default as QueryRequest.k: /ask retrieves before it
    # answers, so it reuses /query's retrieval envelope (DECISIONS.md D3).
    k: int = Field(default=5, ge=1, le=10)


class AskResponse(BaseModel):
    """POST /ask response: the grounded answer plus the source chunks used.

    Reuses QueryResult so each source carries its document_id, chunk, and
    score. sources is always a list, never null — empty when the guardrail
    short-circuits.
    """

    answer: str
    sources: list[QueryResult] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Machine-readable code + human-readable message for one error."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """The single JSON error shape every handler returns: {"error": {"code",
    "message"}}.
    """

    error: ErrorDetail

"""FastAPI app factory: router + exception-handler registration and the
startup lifespan hook only. No business logic — that lives in services/.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Use package-relative imports so the app can be run from the `backend/` folder
from .errors import DocumentNotFoundError, EmptyDocumentError
from .models.schemas import ErrorDetail, ErrorResponse
from .routes.documents import router as documents_router
from .routes.query import router as query_router
from .services import embedding


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the embedding model at boot instead of on the first real request."""
    # Module-qualified call (not `from .services.embedding import _get_model`)
    # so tests' monkeypatched mock is what actually runs here, not a
    # from-import name bound to the real function at import time
    # (DECISIONS.md D2 — Embedding model).
    # The wrapper is async because that's FastAPI's lifespan signature; the
    # actual load is still a plain, blocking sync call — nothing else is
    # running yet, so there's no event loop to freeze (CLAUDE.md rule 9 —
    # concurrency — doesn't apply at startup).
    embedding._get_model()
    yield


app = FastAPI(title="Clickatell Assessment API", lifespan=lifespan)

app.include_router(documents_router)
app.include_router(query_router)


def _error_json(status_code: int, code: str, message: str) -> JSONResponse:
    """Serialize the D5 error shape through its Pydantic model, so error
    bodies are schema-backed like every other response (ASSESSMENT.md tech
    req 5).
    """
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


# Handlers live here, not in routes, per DECISIONS.md D5 (Error handling):
# services raise domain exceptions and stay transport-agnostic; this is the
# one place that maps them to HTTP.
@app.exception_handler(DocumentNotFoundError)
def handle_document_not_found(
    request: Request, exc: DocumentNotFoundError
) -> JSONResponse:
    """Unknown document id -> 404."""
    return _error_json(404, "document_not_found", str(exc))


@app.exception_handler(EmptyDocumentError)
def handle_empty_document(request: Request, exc: EmptyDocumentError) -> JSONResponse:
    """Semantically invalid (empty/whitespace-only) content -> 400."""
    return _error_json(400, "empty_document", str(exc))


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Anything unhandled -> 500, logged, generic message — DECISIONS.md D5
    (Error handling): "500 unexpected (logged)".
    """
    # exc_info=exc, not logger.exception(): sync handlers run in the
    # threadpool where sys.exc_info() is empty — the exception must be
    # passed explicitly to get the stack trace into the log. The client
    # gets a generic message only; internals never leak into responses.
    logging.getLogger("app").error(
        "Unhandled error on %s %s", request.method, request.url.path, exc_info=exc
    )
    return _error_json(500, "internal_error", "An unexpected error occurred")


@app.get("/")
def read_root() -> dict[str, str]:
    """Liveness check — confirms the app is up, nothing more."""
    return {"message": "Hello from Clickatell Assessment API"}

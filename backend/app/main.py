"""FastAPI app factory: router and exception-handler registration and the
startup lifespan hook. No business logic — that lives in services/.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Package-relative imports so the app can be started from the backend/ folder.
from .errors import (
    DocumentNotFoundError,
    EmptyDocumentError,
    EmptyQuestionError,
    LLMServiceError,
)
from .models.schemas import ErrorDetail, ErrorResponse
from .routes.documents import router as documents_router
from .routes.query import router as query_router
from .services import embedding


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the embedding model at boot instead of on the first real request."""
    # Called module-qualified (not a from-import) so the test mock replaces it
    # here. The load is a plain blocking call, which is fine at startup — no
    # requests are being served yet (DECISIONS.md D2).
    embedding._get_model()
    yield


app = FastAPI(title="Clickatell Assessment API", lifespan=lifespan)

app.include_router(documents_router)
app.include_router(query_router)


def _error_json(status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standard JSON error body through its Pydantic model, so errors
    are schema-backed like every other response.
    """
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


# Exception handlers live here, not in the routes: services raise domain
# exceptions and stay transport-agnostic; this is the single place that maps
# them to HTTP status codes (DECISIONS.md D5).
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


@app.exception_handler(EmptyQuestionError)
def handle_empty_question(request: Request, exc: EmptyQuestionError) -> JSONResponse:
    """Semantically invalid (empty/whitespace-only) question -> 400."""
    return _error_json(400, "empty_question", str(exc))


@app.exception_handler(LLMServiceError)
def handle_llm_service_error(request: Request, exc: LLMServiceError) -> JSONResponse:
    """Upstream LLM failure -> 502.

    Registered explicitly: without this, the catch-all Exception handler below
    would swallow it as a 500 and mislabel an upstream outage as our bug.
    """
    return _error_json(502, "llm_service_error", str(exc))


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Anything unhandled -> 500, logged, with a generic client message."""
    # exc_info=exc, not logger.exception(): sync handlers run in the thread
    # pool where sys.exc_info() is empty, so the exception must be passed
    # explicitly to get the stack trace into the log. The client sees only a
    # generic message — internals never leak into responses.
    logging.getLogger("app").error(
        "Unhandled error on %s %s", request.method, request.url.path, exc_info=exc
    )
    return _error_json(500, "internal_error", "An unexpected error occurred")


@app.get("/")
def read_root() -> dict[str, str]:
    """Liveness check — confirms the app is up, nothing more."""
    return {"message": "Hello from Clickatell Assessment API"}

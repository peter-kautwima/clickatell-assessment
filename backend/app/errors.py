"""Domain exceptions, per DECISIONS.md D5 (Error handling): raised in
services/storage, translated to HTTP responses by handlers in main.py so
business logic never imports transport-layer status codes.
"""

from __future__ import annotations


class DocumentNotFoundError(Exception):
    """Raised when a document id does not exist in the store (HTTP 404)."""

    def __init__(self, doc_id: str) -> None:
        """Build the message from the offending id, kept for handlers."""
        super().__init__(f"Document '{doc_id}' not found")
        self.doc_id = doc_id


class EmptyDocumentError(Exception):
    """Raised when uploaded content yields no chunks — empty or
    whitespace-only text (HTTP 400).
    """

    def __init__(self) -> None:
        """Fixed message — there is no per-instance detail to carry."""
        super().__init__("Document content is empty or contains no text")


class EmptyQuestionError(Exception):
    """Raised when a present question is only whitespace (HTTP 400)."""

    def __init__(self) -> None:
        """Fixed message — there is no per-instance detail to carry."""
        super().__init__("Question is empty or contains no text")


class LLMServiceError(Exception):
    """Raised when the upstream LLM call fails — connection error, timeout, or
    a response with no usable answer text (HTTP 502).
    """

    def __init__(self, detail: str) -> None:
        """Carry the upstream failure detail — unlike the fixed-message Empty*
        errors — so the handler's 502 message is informative, per DECISIONS.md
        D4 (LLM integration & prompt design).
        """
        super().__init__(f"LLM service error: {detail}")

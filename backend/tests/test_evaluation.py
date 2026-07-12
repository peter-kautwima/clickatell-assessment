"""Retrieval-quality evaluation harness — the ASSESSMENT.md bonus option:
known Q&A pairs from examples/sample.md, graded automatically.

Opt-in via the `evaluation` marker (run: pytest -m evaluation) because it
uses the REAL local sentence-transformers model: the default suite mocks
embeddings for speed, and a quality measurement against mocked vectors
would measure nothing. No API key involved — the embedding model is local,
and the LLM side stays on the keyless mock, so the harness grades the
retrieval half of the pipeline, the part this architecture controls.
Live-LLM answer grading was considered and rejected: non-deterministic,
needs a key, and grades the model rather than the system (DECISIONS.md
D10, Evaluation harness).
"""

from pathlib import Path

import pytest
from app.services import answering

pytestmark = pytest.mark.evaluation

SAMPLE_DOC = Path(__file__).resolve().parents[2] / "examples" / "sample.md"

# Question -> a fact substring that the correct chunk (and a grounded
# answer derived from it) must contain. Facts are quoted verbatim from
# examples/sample.md — the same corpus that calibrated the D8 threshold.
KNOWN_PAIRS = [
    ("How long is the free trial?", "14-day"),
    ("How much does the Team plan cost per month?", "49 dollars"),
    ("What is the refund window for monthly plans?", "30 days"),
    ("What uptime does the Enterprise plan commit to?", "99.95"),
    ("What happens when the trial ends without a payment method?", "read-only"),
    ("How is customer data encrypted at rest?", "AES-256"),
]

OFF_TOPIC_QUESTION = "How do I teach my dog to sit?"


@pytest.fixture(autouse=True)
def mock_embedding_model():
    """Override conftest's autouse mock with a no-op: this module runs the
    real model, loaded once per process via embedding._get_model's lru_cache.
    """
    yield


@pytest.fixture
def corpus(client):
    """Ingest the sample document through the real HTTP pipeline."""
    response = client.post(
        "/documents",
        json={"title": "Northwind Cloud", "content": SAMPLE_DOC.read_text()},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize(("question", "fact"), KNOWN_PAIRS)
def test_retrieval_finds_known_fact(client, corpus, question, fact):
    """hit@5: the chunk containing the known fact must be retrieved, and it
    must clear the D8 similarity floor so /ask's guardrail wouldn't drop it.
    Asserted per-question (100% on this curated set), not averaged — a
    regression on any single pair should fail loudly.
    """
    body = client.post("/query", json={"question": question, "k": 5}).json()
    scores = [
        (round(r["score"], 3), fact.lower() in r["chunk"].lower())
        for r in body["results"]
    ]
    hits = [s for s, contains in scores if contains]
    assert hits, f"{question!r}: no top-5 chunk contains {fact!r} (scores: {scores})"
    assert max(hits) >= answering.MIN_SIMILARITY, (
        f"{question!r}: best matching chunk scores {max(hits)}, "
        f"under the {answering.MIN_SIMILARITY} guardrail floor"
    )


@pytest.mark.parametrize(("question", "fact"), KNOWN_PAIRS)
def test_ask_returns_fact_bearing_sources(client, corpus, question, fact):
    """End-to-end /ask: every source survives the guardrail floor and the
    known fact is present in the returned sources — the evidence a real
    LLM would answer from. The ANSWER TEXT is deliberately not graded:
    keyless, the mock answers with a fixed-length excerpt of the top chunk
    (so string-matching it grades truncation, not retrieval — measured:
    every known fact sits past the excerpt boundary), and with a key the
    text is non-deterministic. Sources are the deterministic contract.
    """
    body = client.post("/ask", json={"question": question}).json()
    assert body["sources"], f"{question!r}: guardrail returned no sources"
    assert all(s["score"] >= answering.MIN_SIMILARITY for s in body["sources"])
    assert any(fact.lower() in s["chunk"].lower() for s in body["sources"]), (
        f"{question!r}: no returned source contains {fact!r}"
    )


def test_off_topic_question_hits_guardrail(client, corpus):
    """Negative control: an unrelated question must short-circuit with the
    fixed no-content answer and zero sources — the D8 guardrail proven on
    real vectors, not just the suite's mocked ones.
    """
    body = client.post("/ask", json={"question": OFF_TOPIC_QUESTION}).json()
    assert body["answer"] == answering.NO_RELEVANT_CONTENT_MSG
    assert body["sources"] == []

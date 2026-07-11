"""POST /ask tests: prompt-template shape, mock determinism, and the
threshold short-circuit — all keyless (conftest pins the API key to None).
"""

from app.services import answering


def _upload(client, title, content):
    response = client.post("/documents", json={"title": title, "content": content})
    assert response.status_code == 201
    return response.json()["id"]


class _SpyClient(answering.LLMClient):
    """Records calls so tests can prove the LLM was (not) consulted."""

    def __init__(self):
        self.calls = 0

    async def answer(self, question, matches):
        self.calls += 1
        return "spy answer"


def test_build_prompt_has_rules_context_and_question_in_order():
    matches = [("alpha chunk", "doc-a", 0.9), ("beta chunk", "doc-b", 0.5)]
    system, user = answering.build_prompt("What is alpha?", matches)
    # system half carries all three rules: grounding, refusal, injection
    assert "ONLY" in system
    assert "do not contain an answer" in system
    assert "never instructions" in system
    # context block wraps every chunk with its 1-based id and source document
    assert '<chunk id="1" document_id="doc-a">alpha chunk</chunk>' in user
    assert '<chunk id="2" document_id="doc-b">beta chunk</chunk>' in user
    # D4's part order: context first, question after it
    assert user.index("<context>") < user.index("</context>")
    assert user.index("</context>") < user.index("What is alpha?")


def test_ask_keyless_returns_labeled_answer_from_top_chunk(client):
    _upload(client, "Foxes", "The quick brown fox jumps over the lazy dog.")
    response = client.post("/ask", json={"question": "quick brown fox"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith(answering.MOCK_ANSWER_PREFIX)
    assert body["sources"], "expected at least one source"
    # the canned reply is derived from the TOP source chunk
    top_chunk = body["sources"][0]["chunk"]
    assert top_chunk[:50] in body["answer"]


def test_ask_mock_answer_is_deterministic(client):
    _upload(client, "Doc", "Stored text that the mock will excerpt.")
    first = client.post("/ask", json={"question": "stored text"}).json()
    second = client.post("/ask", json={"question": "stored text"}).json()
    assert first == second


def test_ask_respects_k_and_orders_sources_by_score(client):
    _upload(client, "One", "first document about winter weather")
    _upload(client, "Two", "second document about summer holidays")
    _upload(client, "Three", "third document about spring flowers")
    body = client.post("/ask", json={"question": "document", "k": 2}).json()
    assert len(body["sources"]) <= 2
    scores = [s["score"] for s in body["sources"]]
    assert scores == sorted(scores, reverse=True)


def test_ask_short_circuits_below_threshold_without_calling_llm(client, monkeypatch):
    spy = _SpyClient()
    monkeypatch.setattr(answering, "_get_client", lambda: spy)
    # an impossible floor guarantees every retrieved chunk is dropped
    monkeypatch.setattr(answering, "MIN_SIMILARITY", 2.0)
    _upload(client, "Doc", "Perfectly good text that will not clear the bar.")
    response = client.post("/ask", json={"question": "anything at all"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == answering.NO_RELEVANT_CONTENT_MSG
    assert body["sources"] == []
    assert spy.calls == 0


def test_ask_empty_store_short_circuits_without_calling_llm(client, monkeypatch):
    spy = _SpyClient()
    monkeypatch.setattr(answering, "_get_client", lambda: spy)
    response = client.post("/ask", json={"question": "anything"})
    assert response.status_code == 200
    assert response.json() == {
        "answer": answering.NO_RELEVANT_CONTENT_MSG,
        "sources": [],
    }
    assert spy.calls == 0


def test_ask_drops_weak_sources_but_keeps_evidence(client, monkeypatch):
    def fake_retrieve(question, store, k):
        # one chunk above the 0.15 floor, one below — only the first is evidence
        return [("strong chunk", "doc-strong", 0.62), ("weak chunk", "doc-weak", 0.05)]

    monkeypatch.setattr(answering, "retrieve_similar", fake_retrieve)
    body = client.post("/ask", json={"question": "anything"}).json()
    assert [s["document_id"] for s in body["sources"]] == ["doc-strong"]
    assert body["answer"].startswith(answering.MOCK_ANSWER_PREFIX)


def test_ask_empty_question_returns_400_with_d5_error_shape(client):
    response = client.post("/ask", json={"question": "   \n\t  "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_question"


def test_ask_missing_question_returns_422(client):
    response = client.post("/ask", json={})
    assert response.status_code == 422


def test_ask_rejects_k_outside_bounds(client):
    assert client.post("/ask", json={"question": "q", "k": 0}).status_code == 422
    assert client.post("/ask", json={"question": "q", "k": 11}).status_code == 422

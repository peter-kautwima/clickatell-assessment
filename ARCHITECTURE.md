# ARCHITECTURE.md

> System design for the Document Q&A service — the **what & how**. The **why**
> (trade-offs, alternatives rejected) lives in DECISIONS.md; **how to run it**
> lives in README.md. Status: **locked** (design session, Thu 9 July); refined
> only if implementation surfaces a genuine conflict — deviations get flagged
> before code is written.

## System overview

Three pipelines; everything else is bookkeeping on the store.

**Ingestion — POST /documents:** validate `{title, content}` (Pydantic) →
chunk (structure-aware, ≤256-token chunks with overlap) → embed each chunk
(all-MiniLM-L6-v2 → 384-dim vector, normalized to unit length) → store chunks +
vectors + metadata in the VectorStore → return document id + metadata.

**Retrieval — POST /query:** validate `{question}` → embed the question with
the same model → similarity = single `matrix @ vector` dot product against the
normalized store → top-k chunks with scores.

**Answering — POST /ask:** run retrieval → build the grounded prompt
(rules + delimited context + question) → LLM call (Anthropic if key present,
labeled mock otherwise) → return `{answer, sources}` where sources are the
retrieved chunks with scores.

GET /documents, GET /documents/{id}, DELETE /documents/{id} operate on the
store's metadata.

## Requirements → structure trace

| Brief requires                           | Lives at                                                               |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| 6 endpoints                              | `routes/documents.py` (4) + `routes/query.py` (2)                      |
| Chunking, justified                      | `services/chunking.py` + DECISIONS.md §1                               |
| Open-source local embeddings             | `services/embedding.py` wrapping all-MiniLM-L6-v2                      |
| Vector storage + similarity search       | `storage/base.py` (interface) + `storage/memory.py` (normalized numpy) |
| LLM integration, mock acceptable         | `services/answering.py` + `config.py` env toggle                       |
| Pydantic for ALL request/response bodies | `models/schemas.py`                                                    |
| Error handling, proper status codes      | `errors.py` + handlers registered in `main.py`                         |
| "Production structure, not one file"     | module map below: thin routes, logic in services                       |
| Testing, 90%, report included            | `backend/tests/` + conftest mock; coverage table in README             |
| Frontend's 4 features                    | 3 components + typed `api/client.ts`, loading/error states             |
| Part 4 written answers                   | DECISIONS.md §§4.1–4.4                                                 |

## Module map & responsibilities

- `main.py` — app factory, router registration, exception-handler registration,
  startup model load. Zero business logic.
- `config.py` — settings from environment (`ANTHROPIC_API_KEY` presence drives
  the LLM toggle).
- `routes/` — translate HTTP ↔ services; no logic. `documents.py` owns the four
  document endpoints; `query.py` owns /query and /ask.
- `services/chunking.py` — pure functions; the only place split logic exists.
- `services/embedding.py` — model singleton (loaded once at startup); encode
  text → normalized 384-dim vectors. CPU-bound → called from sync paths
  (FastAPI threadpool), never blocking the event loop.
- `services/retrieval.py` — embed question → `store.search(vector, k)`.
- `services/answering.py` — prompt construction + LLM client behind a common
  interface (real Anthropic async client / mock).
- `models/schemas.py` — every Pydantic request/response contract, one place.
- `storage/base.py` — the VectorStore interface. `storage/memory.py` — the
  in-memory implementation.
- `errors.py` — custom exceptions + the JSON error shape.
- `tests/` — unit (chunking, similarity math) + TestClient API tests; embedder
  mocked in `conftest.py` fixtures.

## Key design points

> Numbered by design decision, not by the brief's requirement numbers — the
> trace table above is the requirement→location map. Cross-cutting mandates
> (Pydantic-everywhere, production structure) live in the module map rather
> than as numbered points, because they contain no decision to justify.

### 1. Chunking

Structure-aware splitting (industry name: recursive character text splitting):
split on paragraph boundaries (`\n\n`), merge small paragraphs toward the
target, split oversized ones with overlap. **Target ≈ 180 words / hard ceiling
256 tokens** — the model's max sequence length; anything longer is silently
truncated (model card + maintainer benchmarks: 512-token inputs scored WORSE).
**Overlap 15–20%** (~30 words): boundaries otherwise sever answers from their
subjects, so the answer-bearing chunk loses the term binding it to the
question. Rejected: fixed-size/no-overlap (the Part 2 module's approach).
Deferred: semantic chunking (cost/complexity without assessment payoff).

### 2. Embedding model

all-MiniLM-L6-v2 via sentence-transformers: local + free (brief requirement),
384-dim (small memory footprint), ~80MB one-time download, fast on CPU,
256-token cap that disciplines chunking. Loaded once at startup; encoding runs
off the event loop. Known trade-off: newer models score higher on MTEB —
acceptable at this scale; the service wrapper makes a swap a one-line change.

### 3. Vector storage & search

`VectorStore` interface: `add(doc_id, chunks, vectors)`,
`search(query_vector, k) -> [(chunk, doc_id, score)]`, `delete(doc_id)`,
`list()`. In-memory implementation: one numpy matrix of **unit-normalized**
vectors + parallel metadata. Because vectors are normalized at storage time,
cosine similarity IS the dot product, so scoring all chunks is a single
`matrix @ query` operation — the production fast path, hand-implemented.
Exact (brute-force) search: correct and fast at assessment scale. The
interface exists so a persistent/ANN store (pgvector, ChromaDB) is a one-file
swap — see DECISIONS §4.1.

### 4. Prompt & grounding

Three-part template: (1) role + rules — grounded QA assistant; answer ONLY
from the provided context; if the answer is not in the context, say exactly
that; do not extrapolate; (2) injected context — retrieved chunks wrapped in
clear delimiters with source ids (`<context><chunk id="...">…`); (3) the user
question. `temperature=0` for deterministic output (grounding comes from the
instructions, not the temperature). The endpoint returns the answer AND the
source chunks + scores, so every answer is auditable.

### 5. LLM toggle & mock

`config.py`: key present → real call through the official Anthropic async SDK
(current model string, e.g. `claude-haiku-4-5`; `max_tokens` bounded); key
absent → `MockLLM` implementing the same interface, building the SAME template
and returning a clearly-labeled deterministic answer derived from the top
chunk. One mechanism, three wins: keyless graders can run everything; tests
run deterministic and fast; upstream failure has a defined degradation path.
API errors (timeout, 5xx) raise `LLMServiceError` → HTTP 502 with an
informative message.

### 6. Error handling

Custom exceptions in `errors.py` (`DocumentNotFoundError`,
`EmptyDocumentError`, `LLMServiceError`); handlers registered once in
`main.py`; single JSON error shape `{"error": {"code", "message"}}`.
Status map: 422 validation (Pydantic, automatic) · 404 unknown document id ·
400 semantically invalid input (e.g., empty content) · 502 upstream LLM
failure · 500 unexpected (logged). This is the corrected inverse of the Part 2
module's bare KeyErrors and silent crashes.

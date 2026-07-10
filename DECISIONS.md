# DECISIONS.md — Architecture & Decision Record

> The single design document for this service: system architecture, every
> design decision with its reasoning and rejected alternatives (D1–D7), and
> the Part 4 written answers (4.1–4.4). Per the brief: "DECISIONS.md covering
> Part 4 + architectural choices throughout."
>
> **Reference key:** plain file paths (e.g. `services/chunking.py`) point into
> the repo; D-numbers and §-numbers point to sections of THIS document.
>
> **Status:** all decisions are final (locked in the Thursday design session).
> Two living items only: **D7** fills when the test suite lands (it needs the
> real coverage number), and **4.4** gets my final read-through before
> submission.

---

## 1. System Overview

Three pipelines; everything else is bookkeeping on the store.

**Ingestion — POST /documents:** validate `{title, content}` (Pydantic) →
chunk (structure-aware, ≤256-token chunks with overlap) → embed each chunk
(all-MiniLM-L6-v2 → 384-dim vector, normalized to unit length) → store chunks +
vectors + metadata in the VectorStore → return document id + metadata.

**Retrieval — POST /query:** validate `{question}` → embed the question with
the same model → similarity = a single `matrix @ vector` dot product against
the normalized store → top-k chunks with scores.

**Answering — POST /ask:** run retrieval → build the grounded prompt
(rules + delimited context + question) → LLM call (Anthropic if key present,
labeled mock otherwise) → return `{answer, sources}`.

GET /documents, GET /documents/{id}, DELETE /documents/{id} operate on the
store's metadata.

**How data moves:** routes stay thin — every endpoint validates via a schema,
calls one service function, and returns a schema. Services raise domain
exceptions; handlers registered in `main.py` translate them to HTTP. The store
is the only stateful component.

## 2. Requirements → Structure Trace

| Brief requires (source)                              | Lives at                                                |
| ---------------------------------------------------- | ------------------------------------------------------- |
| 6 endpoints (Part 1, endpoint table)                 | `routes/documents.py` (4) + `routes/query.py` (2)       |
| Chunking, justified (tech req 1)                     | `services/chunking.py` + **D1**                         |
| Open-source local embeddings (tech req 2)            | `services/embedding.py` + **D2**                        |
| Vector storage + similarity search (tech req 3)      | `storage/base.py` + `storage/memory.py` + **D3**        |
| LLM integration, mock acceptable (tech req 4)        | `services/answering.py` + `config.py` + **D4**          |
| Pydantic for ALL bodies (tech req 5)                 | `models/schemas.py` — a mandate, not a decision         |
| Error handling, proper status codes (tech req 6)     | `errors.py` + handlers in `main.py` + **D5**            |
| Production structure, not one file (tech req 7)      | module map, §3                                          |
| RESTful API design + useful docs (eval: API design)  | resource-oriented routes + FastAPI auto-docs at `/docs` |
| Testing, 90% + report included (eval: Testing)       | `backend/tests/` + **D7**; coverage table in README     |
| Service architecture (eval)                          | same as tech req 7 — module map, §3                     |
| Code quality (eval)                                  | CLAUDE.md rules 5 (simplicity) + 8 (docstrings/comments) + the ruff pre-commit gate — no single D-number, enforced by rule + tooling |
| Error handling (eval)                                | same as tech req 6 — `errors.py` + **D5**               |
| AI/RAG reasoning (eval)                              | chunking (**D1**) + embeddings/similarity (**D2**, **D3**) + prompt design (**D4**) together |
| Setup instructions, runnable clean clone (checklist) | `README.md`                                             |
| Frontend's 4 features (Part 3)                       | 3 components + typed `api/client.ts`                    |
| Part 4 written answers (Part 4)                      | **§§4.1–4.4** below                                     |

## 3. Module Map & Responsibilities

- `main.py` — app factory, router + exception-handler registration, startup
  model load. Zero business logic.
- `config.py` — settings from environment (`ANTHROPIC_API_KEY` presence drives
  the LLM toggle).
- `routes/` — translate HTTP ↔ services; no logic. `documents.py` owns the four
  document endpoints; `query.py` owns /query and /ask.
- `services/chunking.py` — pure functions; the only place split logic exists.
- `services/embedding.py` — model singleton (loaded once at startup); encodes
  text → normalized 384-dim vectors. CPU-bound → runs off the event loop.
- `services/documents.py` — the /documents pipeline (chunk → embed → store)
  plus get/list/delete bookkeeping; one function per document endpoint, so
  routes keep the one-service-call shape (§1). _Added on
  feat/storage-documents — see the D3 addendum._
- `services/retrieval.py` — embed question → `store.search(vector, k)`.
- `services/answering.py` — prompt construction + LLM client behind a common
  interface (real Anthropic async client / mock).
- `models/schemas.py` — every Pydantic request/response contract, one place.
- `storage/base.py` — the VectorStore interface; `storage/memory.py` — the
  in-memory implementation.
- `errors.py` — custom exceptions + the JSON error shape.
- `tests/` — unit tests (chunking, similarity math) + TestClient API tests;
  embedder mocked in `conftest.py`.

---

## Design Decisions

### D1 — Chunking

- **Decision:** structure-aware splitting (industry name: _recursive character
  text splitting_) — split on paragraph boundaries, merge small paragraphs
  toward the target, and split oversized ones with overlap.
- **Target ≈180 words; hard ceiling 256 tokens; overlap 15–20% (~30 words).**
- **"Split oversized ones with overlap" means:** most paragraphs fit under the
  ceiling and stay whole; when a _single paragraph_ alone exceeds 256 tokens,
  that paragraph is sliced into ceiling-sized windows, each window repeating
  the last ~30 words of the previous — paragraph-first normally, windowed
  overlap as the fallback for giants.
- **Why the ceiling is physics, not taste:** the all-MiniLM-L6-v2 model card
  states input past 256 word pieces is _silently truncated_, and the
  maintainers' own benchmarks showed 512-token inputs ran ~2x slower AND
  scored worse (the training data was shorter than 256).
- **Why overlap exists:** fixed boundaries sever answers from their subjects —
  a chunk containing "notice within 30 days" that lost the word "refund" to
  the previous chunk stops matching refund questions. Overlap is the insurance
  that every complete idea survives intact in at least one chunk.
- **Rejected:** fixed-size / no-overlap — precisely the approach in the Part 2
  review module, and it fails the boundary case above.
- **Deferred:** semantic chunking (embedding-based boundaries) — cost and
  complexity without assessment payoff; revisited in §4.4.
- **Enforcement is word count, not real tokens — a conservative proxy:**
  `chunk_text()` measures the ~180-word target and 256-token ceiling by
  counting words, not running the model's actual tokenizer, so it stays a
  pure function with no tokenizer/model dependency (§3 module map).
  WordPiece tokenizers run ~1.3–1.4 tokens per English word, so 180 words
  lands around 234–252 tokens — under 256 with a small margin, not exactly
  measured against it. Not an exact guarantee: unusually long or rare words
  (jargon, code, non-English) split into multiple sub-word tokens and could
  still push a chunk past 256 once the real tokenizer runs. Accepted at this
  scale — loading the tokenizer inside chunking.py would couple the chunker
  to the embedding model and slow every chunking test unless also mocked,
  for a precision gain the assessment doesn't need.

### D2 — Embedding model

- **Decision:** **all-MiniLM-L6-v2** via sentence-transformers.
- **Why:** runs locally and free (brief requirement); 384-dim vectors (small
  memory footprint); ~80MB one-time download; fast on CPU; and its 256-token
  cap gives a principled chunk size (D1).
- **Loaded once, warmed at startup:** `_get_model()` is `@lru_cache`-wrapped so
  the model object is built once and reused for the process's lifetime; a
  FastAPI `lifespan` hook calls it once when the app boots so the ~90MB load
  cost lands before traffic arrives, not on whichever request happens to be
  first. `lru_cache` alone only guarantees "loaded once" — it doesn't
  guarantee "before the first request"; the startup hook is what makes that
  true. Encoding itself still runs off the event loop (D6).
- **`lifespan` over `@app.on_event("startup")`:** the simpler `on_event` API
  was tried first but rejected — it's deprecated on the installed FastAPI
  version (0.139.0) and emits a warning on every test run. `lifespan`'s
  wrapper is an async generator (FastAPI's required signature for it), but
  the actual work inside — `embedding._get_model()` — is still one plain,
  blocking, synchronous call; nothing else is running during startup, so
  there's no event loop to freeze and D6's rule doesn't come into play here.
- **Honest trade-off:** newer embedding models score 8–16 points higher on
  MTEB. Accepted at this scale — and the service wrapper makes a model swap a
  one-line change.

### D3 — Vector storage & search

- **Decision:** in-memory numpy behind a small **`VectorStore` interface**:
  `add(doc_id, chunks, vectors)` · `search(query_vector, k) -> [(chunk,
doc_id, score)]` · `delete(doc_id)` · `list()`.
- **Implementation:** one numpy matrix of unit-normalized vectors + a parallel
  metadata list linking each row to its chunk text and document.
- **Vectors arrive already normalized to unit length** — `embedding.py`'s
  `embed_texts()` normalizes at embed time (D2), not storage; by the time
  storage sees a vector it's already unit-length, so `add()` stores it as-is
  and never re-normalizes. That's what makes cosine similarity reduce to the
  raw dot product — scoring every chunk is a single `matrix @ query_vector`
  operation. This is the production fast path (FAISS-style), implemented by
  hand: it demonstrates the similarity math rather than importing it.
- **Search style:** exact (brute-force) — correct and quick at assessment
  scale.
- **Rejected for the build:** ChromaDB/FAISS — the brief calls in-memory
  "perfectly acceptable" and awards bonus for _reasoning about trade-offs_
  (this section); a library would add a dependency while hiding the exact
  understanding being graded.
- **Honest limitation: volatile** — documents don't survive a restart.
  Accepted for the assessment, solved in production by the interface: swap
  `memory.py` for a pgvector/ChromaDB implementation (persistence + ANN
  indexing) **with no other file changing**. That swap is why the interface
  exists. See §4.1.
- **Addendum — interface as built (feat/storage-documents, 2026-07-10;
  flagged and approved before code):** the document-metadata endpoints
  forced two small extensions to the method listing above. (1) `add()`
  carries `title` — GET /documents must return id, title, chunk count,
  upload date (the brief's exact field list), and §1 makes the store the
  ONLY stateful component, so document metadata has to enter through
  `add()`; the store stamps `uploaded_at` itself at add time (field named
  for the brief's "upload date" wording — a clearer-naming choice, not a
  brief mandate; the brief never dictates a JSON key). (2) `get(doc_id)`
  is a fifth method — GET /documents/{id} needs a single-document lookup
  that can signal 404 (raises `DocumentNotFoundError`, per D5). (3) Storage
  speaks its own `StoredDocument` dataclass rather than the Pydantic
  schemas — routes translate — so the HTTP contract can change without
  touching storage, preserving the one-file-swap story.
- **API-shape choices on the document endpoints (same branch):** ids are
  `uuid4().hex` — no shared state, nothing to synchronize (rejected: a
  global counter, the Part 2 review module's approach — racy and guessable).
  GET /documents wraps the array in `{"documents": [...]}` so pagination
  fields can be added without breaking clients (rejected: a bare JSON
  array; §4.1 makes pagination a known production step). POST returns
  **201** + the metadata (§1's "return document id + metadata"); DELETE
  returns **204** with no body (rejected: 200 + a status message — there is
  nothing meaningful to say about a deleted resource).
- **Further honest limitations, same spirit as "volatile":** no locking —
  FastAPI's threadpool can interleave plain-`def` requests, so concurrent
  mutations could in principle race; accepted because assessment usage is
  sequential and D6 rejects manual concurrency machinery (production
  concurrency arrives with the database swap, which owns that problem).
  No document-size cap beyond framework defaults — a production guard is
  one `Field(max_length=...)` away. "Store it" (the brief's POST /documents
  wording) is satisfied by storing chunks + metadata, not the raw original
  text: no endpoint returns the original (GET /{id} is "metadata and its
  chunks"; /ask returns answer + source CHUNKS), so retaining it would be
  dead state.

### D4 — LLM integration & prompt design

- **Decision — the prompt is three parts:** (1) **role + rules** — grounded QA
  assistant; answer ONLY from the provided context; if the answer isn't
  present, say exactly that; no extrapolation. (2) **Injected context** —
  retrieved chunks inside clear delimiters with source ids
  (`<context><chunk id="...">…`). (3) **The user
  question.**
- **Delimiters are XML-style tags** because Anthropic's own prompt-engineering
  guidance recommends XML structure for Claude prompts — we're calling Claude,
  so we use Claude's house style. Delimiters also stop the model confusing
  data (chunks) with instructions.
- **`temperature=0`:** temperature is the sampling-randomness dial; 0 = the
  most probable output every time → reproducible answers and tests. Nuance:
  this buys _determinism_, not _grounding_ — grounding comes from the
  instructions.
- **Auditability:** the endpoint returns answer + source chunks with scores
  (also a brief requirement), so every answer traces to its evidence.
- **Env toggle (`config.py`):** `ANTHROPIC_API_KEY` present → live call via
  the official `anthropic` Python SDK (`pip install anthropic`; the
  `AsyncAnthropic` client reads the key from the environment and handles
  auth/retries/HTTP; current model string, e.g. `claude-haiku-4-5`;
  `max_tokens` bounded). Key absent → **`MockLLM`** implementing the same
  interface, building the SAME template and returning a clearly-labeled
  deterministic answer derived from the top chunk. One mechanism, three wins:
  keyless graders run everything; tests are deterministic and fast; upstream
  failure has a defined degradation path — API errors (timeout, 5xx) raise
  `LLMServiceError` → HTTP 502 with an informative message.

### D5 — Error handling

- **Decision:** custom exceptions in `errors.py` (`DocumentNotFoundError`,
  `EmptyDocumentError`, `LLMServiceError`), raised in services; handlers
  registered once in `main.py`; one JSON error shape
  `{"error": {"code", "message"}}`.
- **Status map:** 422 validation (Pydantic, automatic) · 404 unknown document ·
  400 semantically invalid input (e.g. empty content) · 502 upstream LLM
  failure · 500 unexpected (logged).
- **The 500 leg is a registered catch-all handler** (built on
  feat/storage-documents, after an audit caught it missing): any unhandled
  exception logs with its full stack trace (`exc_info`) and returns the same
  JSON shape with a GENERIC message — exception details never leak into
  responses. Without it, Starlette's default returned plain text, breaking
  the one-error-shape claim.
- **Why:** central handlers keep routes thin and decouple services from the
  transport layer — the corrected inverse of the review module's bare
  KeyErrors and silent crashes.

### D6 — Concurrency model

- **Decision:** framework-level only. I/O-bound work (the LLM call) = async
  endpoints with an async client; CPU-bound work (the embedder) = plain `def`
  paths, which FastAPI runs in its threadpool automatically. No manual threads
  or multiprocessing.
- **Why:** blocking I/O inside `async def` freezes every in-flight request —
  the seeded review bug. Manual threading at this scale adds GIL nuance and
  race conditions on the in-memory store for no gain. At production scale the
  answer is a worker queue, not threads (§4.1).

### D7 — Testing approach

<!-- Claude Code: per CLAUDE.md rule 6, fill this section the day the test
suite lands (Friday). Cover: what's tested and why (unit: chunking edge cases,
similarity math; API: TestClient across happy/edge/error paths per endpoint);
how and why the embedding model is mocked in conftest (determinism + no 90MB
download in CI); the FINAL coverage percentage; where the report lives
(README, pasted table). -->

---

## Part 4 — Architecture & Reasoning

### 4.1 Production readiness (1,000 documents / 100 concurrent users)

The honest first observation: 1,000 documents ≈ 50k chunks × 384 dims × 4
bytes ≈ **~75MB of vectors — RAM is not the constraint**. What actually breaks
in-memory storage at this scale is _statefulness_: 100 concurrent users means
multiple app replicas behind a load balancer, and replicas cannot share
process memory; a restart also erases everything. The changes:

**Storage → persistent, shared, indexed.** Swap `storage/memory.py` for a
pgvector-on-Postgres implementation behind the unchanged `VectorStore`
interface — the one-file swap the interface was designed for. Postgres gives
durability, concurrent access, transactional metadata alongside vectors, and
an HNSW index: approximate nearest-neighbour search replacing brute force,
the correct trade at scale (brute force is exact but O(n) per query). A
dedicated vector DB (Qdrant / Chroma server) is the step after, if vector
features outgrow pgvector.

**Embedding generation → off the request path.** Embedding is the slow,
expensive step, so uploads stop doing it synchronously: POST /documents
returns **202 + a job id**; a worker (SQS/Celery queue) chunks and embeds in
the background **in batches** (the model encodes lists far more efficiently
than one-at-a-time); a status endpoint reports progress. Content-hash caching
means re-uploaded identical text never re-embeds. If throughput demands it,
embedding becomes its own internal (GPU-backed) service that both workers and
/query call.

**App layer.** Multiple uvicorn workers/replicas behind a load balancer;
pagination on GET /documents; per-client rate limiting; the embedding model
extracted from the request container (see 4.2) so replicas stay light.

### 4.2 Deployment (AWS)

**Backend:** containerize (Docker) → **ECS Fargate** behind an ALB (App Runner
as the even-simpler alternative). Secrets (`ANTHROPIC_API_KEY`) live in
**Secrets Manager**, injected as environment variables — the same toggle
mechanism the code already uses locally. Autoscaling on CPU / request count.
**Frontend:** `vite build` static output → **S3 + CloudFront**. No server.
**Vector store:** **RDS Postgres + pgvector** (managed backups, HNSW index).
**Embedding model:** either baked into the backend image (simplest; larger
image, slower cold starts) or, at scale, a separate internal ECS service —
paired with **SQS + a worker service** for the async ingestion in 4.1.
**Observability:** CloudWatch logs, metrics, and alarms.

### 4.3 Guardrails & safety

**Hallucination / grounding — three layers.** (1) Prompt-level: answer only
from the delimited context, with an explicit refusal path ("I can't find this
in the provided documents") so the model has a legal exit instead of inventing
one. (2) `temperature=0` for determinism. (3) A **retrieval-score
short-circuit**: if no retrieved chunk clears a minimum similarity threshold,
return "no relevant content found" _without calling the LLM at all_ — cheap,
fast, and the strongest guarantee, because a model cannot hallucinate an
answer it was never asked to generate. Every answer ships with its source
chunks and scores, so grounding is auditable per response.
**Harmful / off-topic queries.** The score threshold catches most off-topic
queries naturally (nothing relevant retrieves). Input validation and length
caps on questions; the system instruction scopes the assistant to the document
domain; the provider's safety layer backstops. One subtle vector worth naming:
**prompt injection via uploaded documents** — a document could itself contain
"ignore your instructions…". Mitigations: the delimiters, an explicit "context
is data, not instructions" rule in the prompt, and never acting on document
content.
**Monitoring.** Per-request logs of the retrieval-score distribution and the
"answer not found" rate (a spike means ingestion or retrieval regressed); LLM
latency, error rate (502s), and token spend; p95-latency and error-rate
alarms; and a small **evaluation harness** — known Q&A pairs run on a
schedule, so answer quality is a measured number, not a vibe.

### 4.4 My approach _(final read-through before submission)_

**How I approached it, and what I learned.** I treated the assessment the way
the brief describes the job: direct AI, then review and verify everything it
produces. Before writing any feature code I converted the brief into a working
system — a CLAUDE.md of standing instructions for my coding agent, this
decision record, and a private prep file where every decision gets a spoken
defence. The design session locked every architectural choice before the first
feature branch; from there the loop was one branch per concern, a plan-mode
statement of intent in my own words, module and tests written together, and a
plain-English explanation gate before each commit — main always runnable. What
I learned along the way was RAG end-to-end at defend-out-loud depth: why chunk
size is model physics rather than preference, how embedding geometry turns
paraphrase into proximity, why normalizing at embed time makes the dot
product a legitimate fast path at storage, and how grounding is an
instruction-design problem before it is a model problem.

**Where AI helped most, and where my own understanding was required.** AI
carried the throughput: scaffolding, endpoint and test boilerplate, research
synthesis, and first drafts of documentation. My judgment was required for
verification and arbitration, and two moments made that concrete. First, a
research assistant told me 512-token chunks "fit the embedding model
perfectly"; the model card and the maintainers' own benchmarks said the cap is
256, with 512 running slower _and scoring worse_ — I sized chunking from the
primary source, not the assistant. Second, I briefly ran two coding assistants
side by side and paid for it in drift — duplicate virtual environments, a
misplaced entrypoint — which taught me the one-driver rule: a single agent
under a single instruction file, and everything produced outside it gets
audited before it merges. I also kept the tooling itself deliberately
minimal — one agent, one instruction file, a ruff pre-commit hook, and
nothing more (no subagents, no parallel generation) — because parallel output
outpaces exactly the review capacity this role tests, and the assessment
grades the artifact, not the tooling around it.

**The hardest part.** Python's concurrency model, coming from Node. The
async/await words are identical, but the failure mode is different: one
blocking call inside an async endpoint freezes every in-flight request — the
exact bug seeded in the Part 2 review module. I worked through it by turning
the lesson into standing rules (async client for I/O-bound work, plain `def`
and the threadpool for the CPU-bound embedder) and by treating the review
module as a mirror: every flaw I had to critique there became an explicit
rule in my own service. The quieter second challenge was knowing when to stop
designing and start building — solved by locking this record and enforcing
"main is always runnable."

**With two more days.** An evaluation harness first — known Q&A pairs scoring
retrieval and answer quality, because it converts every other improvement
into a measured number. Then contextual retrieval (prepending document
context to each chunk before embedding), a persistent pgvector store behind
the existing interface, and streaming /ask responses to the frontend.

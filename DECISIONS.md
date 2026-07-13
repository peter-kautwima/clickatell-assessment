# DECISIONS.md — Architecture & Decision Record

> The single design document for this service: system architecture, every
> design decision with its reasoning and rejected alternatives (D1–D10), and
> the Part 4 written answers (4.1–4.4). Per the brief: "DECISIONS.md covering
> Part 4 + architectural choices throughout."
>
> **Reference key:** plain file paths (e.g. `services/chunking.py`) point into
> the repo; D-numbers and §-numbers point to sections of THIS document.
>
> **Status:** the core architecture (D1–D7) was locked in the Thursday design
> session; D8–D10 record decisions made during the build, same day they were
> made. D7 carries the real coverage number. One living item: **4.4** gets my
> final read-through before submission.

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
  No defensive shape re-validation inside `add()`/`search()` — the store
  trusts its single caller, since the ingestion service guarantees each
  chunk has exactly one vector before storage ever sees them; a production
  store crossing a process boundary would re-check, but here it would guard
  against a caller that cannot exist. And `DocumentCreate.title` uses
  `Field(min_length=1)`, which rejects an empty title (422) but not a
  whitespace-only one — a `.strip()` validator is the trivial production
  tightening, left out at this scale because a blank-looking title harms
  only the person who typed it.
- **Query endpoint choices (feat/query-search, 2026-07-11):** `/query`
  defaults to `k=5` and lets clients override `k` from 1 to 10. Five chunks
  is the small default because D1's target is ~180 words per chunk, so a
  normal response returns about **900 words** of evidence — enough breadth
  for a user to see competing matches without flooding the API response or
  the next branch's `/ask` prompt. The maximum of 10 is the escape hatch for
  broader questions while still bounding context to about **1,800 target
  words** (and at D1's 256-token hard ceiling, no more than **2,560 chunk
  tokens** before prompt overhead). Rejected alternatives: fixed `k` (too
  rigid for broad questions) and unbounded client `k` (turns one request
  into an accidental prompt/response-size blow-up). Empty/whitespace
  questions are **400** via D5, not 422: the `question` field is present and
  type-valid, but semantically unusable — the same line as empty document
  content. A `question` length cap was also considered and rejected: /query
  is a repeatedly-hittable endpoint, so a per-field cap guards only the
  single-huge-request case and does nothing against repeated modest-sized
  abuse — the real control is rate limiting, already named a production
  step in §4.1 — and the embedding model silently truncates input past 256
  tokens anyway (D1), so an oversized question degrades gracefully instead
  of failing. Same posture as the no-document-size-cap line above.

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
- **Addendum — model choice & request envelope (feat/ask-llm-completion,
  2026-07-11):** the live model is **`claude-haiku-4-5`**, a recorded choice,
  not a placeholder. Grounded QA over at most ten short chunks is a simple,
  latency- and cost-sensitive task, and Haiku 4.5 is the cheapest, fastest
  current tier ($1 / $5 per million input / output tokens) that still accepts a
  `temperature` parameter — the newest tiers (Fable 5, Opus 4.8, Sonnet 5)
  reject sampling params with a 400, so `temperature=0` stays legal here.
  _Rejected:_ defaulting to a larger Opus/Sonnet model — more capable but
  roughly 3–10x the cost and slower, for no measurable gain on a task whose
  answer must come verbatim from ≤10 short chunks; the service wrapper keeps a
  swap a one-line change (`ANTHROPIC_MODEL`). Request envelope: `max_tokens =
  1024` (~750 words — ample for a grounded answer, and a hard per-call cost
  cap), `timeout = 30s`, `max_retries = 1` (the SDK retries timeouts too, so a
  dead upstream fails at ~1 minute worst-case rather than ~1.5 with the SDK
  default of 2). The key is passed **explicitly** to `AsyncAnthropic`
  (correcting the "reads the key from the environment" note above):
  pydantic-settings loads `.env` without exporting to `os.environ`, so the
  SDK's own env lookup would find nothing. The client is built **per request,
  uncached** — nothing connects until the call fires, and a cached client would
  pin its connection pool to whichever event loop built it first. As-built
  names: an `LLMClient` interface with `MockLLMClient` / `AnthropicLLMClient`,
  selected by `_get_client()`.
- **Addendum — a refusal is not a 502 (same branch):** a model refusal
  (`stop_reason == "refusal"`) is a valid upstream answer, not a failure, so it
  returns **200** with a polite in-band message. The refusal is checked BEFORE
  reading content, because a refused response can carry an empty content list.
  Only a genuine SDK failure (connection / timeout / 5xx, caught as
  `anthropic.APIError`) or a "successful" response with no text block at all
  (e.g. `max_tokens` exhausted before any text) raises `LLMServiceError` → 502.
- **Addendum — delimiters are escaped, not merely trusted
  (fix/external-audit-hardening, 2026-07-13):** `build_prompt` XML-escapes both
  the chunk text and the `document_id` attribute before inserting them between
  the `<chunk>`/`<context>` tags. Without escaping, a document containing a
  literal `</chunk></context>` could close the delimiters early and place its
  own text _outside_ the context block — the exact injection channel the
  delimiters exist to close. Escaping makes the tag structure un-forgeable, so
  the "context is data, not instructions" rule above becomes a second layer
  rather than the only one. _Rejected:_ leaning on the system-prompt
  instruction alone — it asks the model to behave, where escaping removes the
  ability to misbehave. The mock path answers from the raw top chunk (not the
  assembled prompt), so keyless behaviour is byte-identical.
- **Addendum — `.env` is resolved from the file, not the working directory
  (same branch):** `config.py` anchors `env_file` to
  `Path(__file__).resolve().parents[1] / ".env"` (i.e. `backend/.env`).
  pydantic-settings resolves a bare `".env"` against the process working
  directory, and README documents two equivalent launch directories (repo root
  and `backend/`); started from the root, a bare path silently missed
  `backend/.env`, so the key toggle above never saw a configured key and /ask
  quietly ran the mock. _Rejected:_ documenting a single launch directory —
  that "fixes" the mismatch by deleting a working option instead of the bug. A
  missing `.env` is still tolerated (settings fall back to the mock), so this
  changes only _where_ a present file is found, never whether one is required.

### D5 — Error handling

- **Decision:** custom exceptions in `errors.py` (`DocumentNotFoundError`,
  `EmptyDocumentError`, `EmptyQuestionError`, `LLMServiceError`), raised in
  services; handlers registered once in `main.py`; one JSON error shape
  `{"error": {"code", "message"}}`.
- **Status map:** 422 validation (Pydantic, automatic) · 404 unknown document ·
  400 semantically invalid input (e.g. empty content or question) · 502
  upstream LLM failure · 500 unexpected (logged).
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
- **Addendum — /ask dispatch (feat/ask-llm-completion):** POST /ask is the
  service's one `async def` endpoint (the I/O-bound LLM call is awaited on the
  loop). Its retrieval step embeds the question, which is CPU-bound, so
  `answer_question` runs `retrieve_similar` through `run_in_threadpool` — the
  same AnyIO pool FastAPI gives the plain-`def` endpoints. Net effect: /ask's
  embed step has identical concurrency semantics to /query, and a slow LLM call
  never stalls other requests.

### D7 — Testing approach

- **What's tested, and why.** Two layers. **Unit:** chunking edge cases
  (paragraph merge toward the target, overlap-windowing of an oversized
  paragraph, empty / whitespace input) and the similarity math (exact dot
  products, top-k ordering, delete-masking) — the pure logic that must be
  provably correct. **API (TestClient):** every endpoint across happy / edge /
  error paths — upload + metadata, the list / get / delete lifecycle, /query
  ranking and k-bounds, and /ask across its mock answer, the guardrail
  short-circuit, per-chunk source filtering, and the live toggle. Error paths
  assert the single D5 JSON shape and the 400-vs-422 split (semantic vs
  schema-shape) on every endpoint.
- **The embedding model is mocked in `conftest.py`** — a deterministic fake
  standing in for SentenceTransformer — for determinism (identical input →
  identical vector, no sampling) and speed (no ~90MB download in CI, sub-second
  suite); the startup lifespan runs against the same mock. The one application
  line this leaves uncovered is the real `SentenceTransformer(...)` load, by
  design.
- **The LLM is never called for real.** An autouse fixture pins the API key to
  `None`, so the suite runs the mock path by default; the live-Anthropic tests
  swap the async SDK client for an attribute-faithful fake and assert the exact
  request envelope — zero network calls, no key required.
- **Coverage: 99%** — 351 statements, a single uncovered line (the mocked model
  load), across 61 tests; every application module bar that one line is at
  100%. The full report is reproduced in README.

### D8 — /ask similarity threshold & source filtering

- **Decision:** before answering, drop every retrieved chunk whose cosine score
  is below **`MIN_SIMILARITY = 0.15`** from BOTH the prompt and the returned
  sources; if nothing survives, answer "no relevant content found" **without
  calling the LLM at all** (the §4.3 short-circuit — a model cannot hallucinate
  an answer it was never asked to generate). The floor lives only on the /ask
  path in `answering.py`; /query keeps returning raw top-k.
- **The floor is measured, not guessed.** Calibrated 2026-07-11 through the
  service's own pipeline (`chunk_text` → `embed_texts` →
  `InMemoryVectorStore.search`) on `examples/sample.md` plus two off-topic
  control documents (sourdough, football offside). Top scores per question:

  | kind | question | top score |
  |---|---|---|
  | relevant | How long does the trial last before I pay? | 0.453 |
  | relevant | What happens to my data if I cancel? | 0.528 |
  | relevant | Is my information encrypted? | **0.227** ← floor driver |
  | relevant | Can I get my money back after a charge? | 0.383 |
  | adjacent | Does Northwind Cloud offer a mobile app? | 0.510 |
  | adjacent | Which programming languages are supported? | 0.146 |
  | unrelated | What is the capital of France? | 0.048 |
  | unrelated | How do I teach my dog to sit? | 0.052 |

  The gap between real answers (≥ 0.227) and noise (≤ 0.052) puts **0.15** at
  ~3x the noise ceiling with ~50% margin under the weakest true positive.
- **Two lessons the numbers taught.** (1) A pre-measurement guess of 0.25–0.40
  would have wrongly refused the encryption question — a short question against
  a ~180-word chunk compresses cosine, so the true-positive floor sits lower
  than intuition suggests. (2) The 0.510 "mobile app" adjacent case proves the
  threshold cannot catch on-topic-but-unanswerable questions; that is the
  prompt-level refusal rule's job (D4). Two layers, each doing only what it can
  (§4.3).
- **Rejected:** a single defence. The threshold alone lets an on-topic question
  with no answer through; the prompt rule alone still spends an LLM call on pure
  noise. Together they are cheap first, safe second.

### D9 — Frontend/backend integration (proxy, TypeScript strictness)

- **Context:** the frontend's `api/types.ts`/`api/client.ts` had drifted from
  the backend contract above (multipart file upload instead of JSON
  `{title, content}`, no `/ask` call, no error-shape handling), and neither
  a Vite dev proxy nor backend CORS existed, so no request from the frontend
  dev server could reach the backend at all.
- **Decision — Vite dev proxy, not backend CORS middleware.**
  `frontend/vite.config.ts` gets an explicit `server.proxy` entry per path
  (`/documents`, `/query`, `/ask` → `http://localhost:8000`), and
  `api/client.ts` uses a relative `BASE_URL = ""` so requests are same-origin
  from the browser's point of view.
  - **Why:** stays entirely inside `frontend/` (no backend file touched);
    matches the structure this project already committed to — the target
    tree comment on `vite.config.ts` reads `# dev proxy → backend, avoids
    CORS setup`, so this finishes an existing design rather than introducing
    a new one.
  - **Rejected:** `CORSMiddleware` in `backend/app/main.py`. Equally small
    (~5–10 lines), but touches a backend file for a frontend-scoped task,
    and nothing in this document previously named CORS as the intended
    mechanism.
  - **Known gap, not resolved here:** production serves the frontend as a
    static `vite build` bundle from S3 + CloudFront (§4.2) with no dev
    server, so this proxy cannot exist in that topology. Production will
    need either backend `CORSMiddleware` or a CloudFront path-based route to
    the ALB origin — a follow-up, out of scope for this frontend branch.
- **Decision — enable TypeScript `strict: true` now, not deferred.**
  Added to `frontend/tsconfig.app.json` before any component code was
  rewritten.
  - **Why:** the brief's frontend rubric line is a typed `api/client.ts`
    with no `any` — without `strict` (specifically `noImplicitAny` and
    `strictNullChecks`), TypeScript accepts implicit `any` in untyped catch
    bindings and loosely-inferred `fetch`/`json()` results even when the
    literal keyword `any` never appears, so the flag is load-bearing for
    that claim, not cosmetic. Enabling it before writing the real
    `types.ts`/`client.ts`/components meant every line was authored
    correctly the first time, instead of a second retrofit pass over five
    files that were about to be rewritten anyway.
- **Decision — file "upload" is a client-side read, not a multipart
  endpoint.** The upload form accepts pasted text and also offers a
  `.txt`/`.md` file picker, but the file is read in the browser
  (`file.text()`) and submitted through the same JSON
  `POST /documents {title, content}` contract — the backend has no
  multipart endpoint and gains none.
  - **Why:** the brief's frontend requirement is "form/interface to paste
    or upload text content with a title" — both halves are satisfied
    without touching the backend contract, adding a parser, or a second
    upload path to test. The filename (extension stripped) pre-fills the
    title when it's empty.
  - **Rejected:** a backend multipart endpoint. It would duplicate the
    ingestion path for zero functional gain at this scope — the file types
    accepted (plain text/markdown) are exactly what the JSON field already
    carries. PDF extraction is the stretch-goal case that would justify it,
    and that is explicitly out of scope.
- **Decision — brand-aligned styling via role-named CSS tokens, no
  framework.** `frontend/src/index.css` opens with a commented brand-token
  block (the de-facto style guide): Clickatell navy `#0a1e42`, CTA green
  `#8dc63f`, and cyan, applied through role names (`--bg-card`,
  `--action`, `--accent`, …) so raw hexes exist in exactly one place. Both
  color schemes follow `prefers-color-scheme` — light mirrors the
  marketing site (white/navy/green), dark mirrors the slide decks
  (navy/white/green). Two measured accessibility calls: the green button
  carries NAVY text, not white (white-on-green is 2.04:1, failing WCAG AA;
  navy-on-green is 8.05:1), and the light-mode cyan focus ring is darkened
  from the brand's `#35b7e8` (2.31:1 on white, under the 3:1 non-text
  minimum) to `#0f8ec4` (3.4:1+). Every text/background pair in both
  schemes measures ≥6.5:1.
  - **Rejected:** a CSS framework (Tailwind) or a separate style-guide
    document. At three components the framework costs more than it saves,
    §4.4 already stakes out minimal tooling as this project's position,
    and the brief states design/CSS skill is explicitly not graded — the
    commented token block IS the style guide, at zero extra collateral.
- **Decision — source scores rendered as TREC relevance labels plus the
  named quantity.** Each Q&A source line reads
  "**Highly relevant** · cosine similarity 0.510" with a one-line
  explainer under the Sources heading. Terminology comes from NIST TREC
  graded relevance judgments (trec.nist.gov: highly relevant / relevant /
  not relevant) — "not relevant" never renders because the D8 similarity
  floor (0.15) filters it, so the guardrail literally implements TREC's
  bottom grade. The 0.45 label cutoff is calibrated, not conventional:
  every measured correct answer across the D8 calibration and D10
  evaluation runs scored 0.23–0.53, so ≥ 0.45 marks the top of the
  true-answer range. Cosine magnitudes are not comparable across
  embedding models, so no universal threshold exists to borrow —
  published work tunes per task (e.g. an optimized 0.671 for MPNet
  paraphrase detection) and empirical calibration is the standard
  practice.
  - **Rejected:** a bare number ("score: 0.338" means nothing to any
    audience); a confidence percentage (nothing in the pipeline emits
    calibrated confidence — a fabricated % invites "how is that
    computed?" with no good answer); rescaling against the observed ~0.6
    ceiling (an observed maximum, not a mathematical bound — a
    legitimate 0.65 would render past 100%); surfacing the D10
    evaluation results in the UI (test results about the sample corpus
    say nothing about the user's own question — there is no answer key
    for arbitrary questions). The answer itself carries no score by
    design: similarity is measured per chunk, while the answer is
    synthesized from several — its quality mechanism is the D8 guardrail
    refusal, not a fabricated number.
- **Decision — no `k` control added to the Q&A form.** The backend's
  `AskRequest.k` (default 5, bounded 1–10) is left to its default; the
  frontend never sends it. Confirmed with the requester as an explicit
  scope call, not a default: adding it was assessed as cheap but not
  necessary for the assignment's stated Q&A feature set, and skipping it
  keeps the form to one input.
- **Addendum — final-audit UX fixes (audit/final-review, 2026-07-12), none
  touching the backend contract:**
  (1) **Backend-unreachable is one normalized failure, not raw gateway
  text.** Measured behavior: with the backend stopped, the Vite dev proxy
  answers **502 with a `text/plain` body** (verified with curl against the
  running dev server), and with no server listening at all, `fetch` rejects
  with a browser TypeError — both previously leaked raw "Bad Gateway" /
  generic text into panel error regions, once per action. `api/client.ts`
  now folds both into a single `backend_unreachable` error. The inference is
  sound for this system specifically: `main.py`'s catch-all handler
  guarantees even 500s leave the app as the D5 JSON shape, so a 502/503/504
  whose body is NOT one of the two known JSON error shapes cannot have come
  from the app. The backend's own JSON 502 (`llm_service_error`) passes
  through untouched. App.tsx renders one banner with a retry; all panels
  route the unreachable case there instead of stacking local copies.
  _Rejected:_ a global fetch wrapper/error boundary or a toast system —
  three components sharing one banner does the job with no new machinery.
  (2) **Q&A gated until a document exists** — input and Ask button disabled
  with an "upload a document first" hint; asking against an empty store can
  only ever produce the D8 no-content guardrail answer, so the UI now says
  why up front. The hint waits for the document list to finish loading so it
  never flashes mid-fetch.
  (3) **Delete failures surface in the list's alert region** — previously
  console-only, behind a comment that wrongly claimed the shared error
  region caught it (it only ran on success; the comment is gone).
  Cosmetic, same pass: the Ask button sits flush against the question input
  as one search-bar row, and the browser tab is titled "Document Q&A"
  instead of the starter's "frontend".

### D10 — Evaluation harness (bonus)

- **Decision:** the optional bonus is the evaluation harness —
  `backend/tests/test_evaluation.py`, known Q&A pairs from
  `examples/sample.md` graded automatically over the real HTTP pipeline
  (upload → chunk → embed → retrieve → ask). Opt-in via a registered
  pytest marker: `pytest.ini` deselects `evaluation` by default
  (`addopts = -m "not evaluation"`), and `pytest -m evaluation` runs it.
- **Why a marker and not a flag:** the harness must use the REAL
  sentence-transformers model — the ordinary suite mocks embeddings for
  speed, and measuring search quality against mocked vectors measures
  nothing. A considered-and-rejected `--run-eval` CLI flag (or env var)
  toggling the mock inside conftest.py would flip ALL 59 existing tests
  onto the real model when passed — slow, and semantically wrong since
  those tests were written against deterministic fake vectors — so test
  selection would still be needed on top, i.e. markers anyway. The marker
  plus a module-level fixture override (the eval module redefines the
  autouse `mock_embedding_model` as a no-op) does selection and model
  choice in one mechanism, and leaves conftest.py untouched.
- **What is graded, and what deliberately is not:** (1) retrieval hit@5 —
  for each of six questions, some top-5 chunk contains the known fact,
  scoring above the D8 floor (0.15); asserted per question at 100% on
  this curated set, not averaged, so any regression fails loudly.
  (2) /ask end-to-end — sources survive the guardrail and contain the
  fact. (3) A negative control — an off-topic question returns the fixed
  guardrail answer with zero sources, proving the D8 short-circuit on
  real vectors. **Answer TEXT is deliberately not graded:** keyless, the
  mock answers with a fixed 200-char excerpt of the top chunk, so
  string-matching the answer grades excerpt truncation, not retrieval —
  measured: every known fact sits past the excerpt boundary. With a key,
  live answers are non-deterministic and would grade the model, not this
  system. Sources are the deterministic contract.
- **Measured results (2026-07-12, real model):** fact-bearing chunk rank
  and top-5 scores per question — trial length: rank 1 (0.476) · Team
  price: rank 1 (0.510) · refund window: rank 1 (0.477) · Enterprise
  uptime: rank 3 (top-5 0.519/0.505/0.450) · trial expiry: rank 2
  (0.342/0.321) · encryption at rest: rank 1 (0.286). hit@5 = 6/6; all
  fact chunks clear the 0.15 floor; guardrail control passes. The uptime
  question ranking its fact chunk third is the concrete argument for
  returning k=5 sources rather than only the best chunk.
- **No app code changed** — the harness is pure test collateral; default
  suite remains 61 tests / 99% coverage, byte-identical behavior.

---

## Part 4 — Architecture & Reasoning

### 4.1 Production readiness (1,000 documents / 100 concurrent users)

The honest first observation: 1,000 documents ≈ 50k chunks × 384 dims × 8
bytes ≈ **~150MB of vectors — RAM is not the constraint**. (`memory.py` stores
the matrix as numpy's default `float64`; the model emits `float32`, so casting
at store time halves this to ~75MB — a one-line production optimization, not a
change worth making at assessment scale where the point stands either way.)
What actually breaks
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
CloudFront also path-routes the three API prefixes (`/documents`, `/query`,
`/ask`) to the ALB origin, replacing the dev-only Vite proxy (D9's known
gap) — same-origin from the browser's view, so no CORS configuration and no
hard-coded API host in the bundle.
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
schedule, so answer quality is a measured number, not a vibe. That harness
is not hypothetical: it exists in this submission (D10, the bonus — six
known Q&A pairs graded over the real pipeline); production would run
exactly it on a schedule against the live corpus.

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

**The last day was an audit, not a build.** Before submission I turned the
Part 2 review lens on my own repo: a strictly read-only pass first — the
full validation suite, every endpoint probed against the live server, a
documentation-consistency sweep — findings ranked by severity, then fixes
applied one small commit at a time. It caught real defects in my own work,
the most instructive being a comment that claimed delete failures surfaced
in the UI when the code only logged them to the console — exactly the class
of flaw I criticised in the review module, found on my side of the fence.
The fixes followed the same measure-first habit as D8: the frontend's
backend-down handling was written only after curl showed what the dev proxy
actually returns with the backend stopped (a 502 with a text/plain body),
not from an assumption about it.

**With two more days.** The evaluation harness topped this list until the
final weekend, when it became the built bonus (D10) — the right first pick
precisely because it converts every other improvement into a measured number.
Next would be contextual retrieval (prepending document context to each chunk
before embedding, graded against that same harness), a persistent pgvector
store behind the existing VectorStore interface, and streaming /ask responses
to the frontend.

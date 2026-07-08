# ARCHITECTURE.md

> System design for the Document Q&A service — the **what & how**. The **why**
> (trade-offs, alternatives rejected) lives in DECISIONS.md; **how to run it**
> lives in README.md.
> **Status: skeleton** — sections filled during the Wed design session, refined
> during the build.

## System overview

<!-- TODO tonight: the three-pipeline narrative in ~10 lines —
Ingestion (POST /documents): validate → chunk → embed → store.
Retrieval (POST /query): embed question → cosine top-k → chunks + scores.
Answering (POST /ask): retrieval → grounded prompt → LLM (or mock) → answer + sources.
Everything else is bookkeeping on the store. -->

## Requirements → structure trace

| Brief requires                           | Lives at                                                           |
| ---------------------------------------- | ------------------------------------------------------------------ |
| 6 endpoints                              | `routes/documents.py` (4) + `routes/query.py` (2)                  |
| Chunking, justified                      | `services/chunking.py` + DECISIONS.md §1                           |
| Open-source local embeddings             | `services/embedding.py` wrapping all-MiniLM-L6-v2                  |
| Vector storage + similarity search       | `storage/base.py` (interface) + `storage/memory.py` (numpy cosine) |
| LLM integration, mock acceptable         | `services/answering.py` + `config.py` env toggle                   |
| Pydantic for ALL request/response bodies | `models/schemas.py`                                                |
| Error handling, proper status codes      | see Error handling section below                                   |
| "Production structure, not one file"     | the module map below: thin routes, logic in services               |
| Testing, 90%, report included            | `backend/tests/` + conftest mock; coverage table in README         |
| Frontend's 4 features                    | 3 components + typed `api/client.ts`, loading/error states         |
| Part 4 written answers                   | DECISIONS.md §§4.1–4.4                                             |

## Module map & responsibilities

<!-- TODO tonight: one line per module. Full tree lives in CLAUDE.md — here,
WHO owns WHAT: routes translate HTTP ↔ services and hold zero logic; services
own the pipelines; models/schemas.py is the single contract source; storage
hides the persistence choice behind the VectorStore interface. -->

## Data flow

### Ingestion — POST /documents

<!-- TODO -->

### Retrieval — POST /query

<!-- TODO -->

### Answering — POST /ask

<!-- TODO -->

## Key design points (one per design-session decision)

### 1. Chunking

<!-- TODO tonight, after my playback: paragraph-aware ~180-word target,
15–20% overlap, oversized-paragraph fallback split; sized by MiniLM's
256-token truncation limit. -->

### 2. Embedding model

<!-- TODO — agenda item 2: why all-MiniLM-L6-v2 (local, free, CPU-fast,
384-dim, and the 256-token cap that disciplines chunk size). Loaded once at startup. -->

### 3. VectorStore interface

<!-- TODO — agenda item 3: exact methods (add / search / delete / list),
the search contract (returns chunks + scores), normalize-at-storage decision. -->

### 4. Prompt & grounding

<!-- TODO — agenda item 4: template structure, context injection format,
grounding instruction ("answer only from context; say so if absent"). -->

### 5. LLM toggle & mock

<!-- TODO — agenda item 5: env-var switch in config.py, what the mock returns,
why the same mechanism covers keyless graders, API failure, and tests. -->

### 6. Error handling

<!-- TODO — agenda item 6: custom exception types, the status-code map
(400 / 404 / 422 / 502 …), where handlers register. -->

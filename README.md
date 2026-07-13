# Document Q&A Service — Clickatell Technical Assessment

A small document intelligence service: upload text/markdown documents, then ask
natural-language questions answered from their content. Classic RAG pipeline:
chunking → local embeddings → similarity search → grounded LLM answer with sources.

**Stack:** FastAPI · sentence-transformers (all-MiniLM-L6-v2, runs locally) ·
in-memory vector store · React + TypeScript (Vite)

**Companion docs:** [DECISIONS.md](DECISIONS.md) — architecture, every design
decision with reasoning, and Part 4 · [CODE_REVIEW.md](CODE_REVIEW.md) — Part 2


https://github.com/user-attachments/assets/25266464-353e-4595-9a0f-957c50cf8077


---

## Prerequisites

- Python 3.11 or 3.12
- Node.js 20+
- _(Optional)_ an Anthropic API key — **without one, `/ask` runs against a
  built-in mock** that uses the real prompt template, so the whole service is
  runnable keyless.

## Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env         # add ANTHROPIC_API_KEY=... for live answers (optional)
```

- **First install is the slow step:** `pip install` pulls PyTorch (several
  hundred MB) as a sentence-transformers dependency — allow a few minutes.
  The embedding model itself (~90 MB) downloads the first time you **start**
  the server (not the first request) — the app warms it during startup, so
  expect a pause before "Application startup complete" appears the first
  time; one-time cost, cached after that.
- Interactive API docs once running: http://localhost:8000/docs

### Run the backend

Two equivalent ways to start it — pick whichever fits your terminal setup.

Option A — from the repo root:

```bash
source backend/venv/bin/activate      # Windows (PowerShell): backend\venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

Option B — from `backend/`:

```bash
cd backend
source venv/bin/activate              # Windows (PowerShell): venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Both options load the same configuration: `backend/.env` is resolved from the
code's own location, not your current directory, so the optional API key is
picked up from either starting point.

If port 8000 is busy, add `--port 8001`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 — dev proxy forwards API calls to the backend
```

## Running tests & coverage

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

### Evaluation harness (bonus)

The default suite mocks the embedding model for speed, so it can't measure
retrieval quality. A separate opt-in harness grades the system against
known Q&A pairs from `examples/sample.md` using the real local embedding
model (no API key needed — the LLM side stays on the keyless mock):

```bash
cd backend
pytest -m evaluation
```

It checks that the chunk containing each known fact is retrieved in the
top 5 with a score above the /ask relevance floor, that /ask returns
fact-bearing sources end to end, and that an off-topic question triggers
the "no relevant content" guardrail instead of a made-up answer. The model
loads from the local cache (first-ever run downloads ~90MB).

### Coverage report

From `pytest --cov=app --cov-report=term-missing` (59 tests):

| Module | Stmts | Miss | Cover |
| ------------------------- | ----: | ---: | ---: |
| app/\_\_init\_\_.py | 0 | 0 | 100% |
| app/config.py | 5 | 0 | 100% |
| app/errors.py | 14 | 0 | 100% |
| app/main.py | 38 | 0 | 100% |
| app/models/schemas.py | 35 | 0 | 100% |
| app/routes/documents.py | 28 | 0 | 100% |
| app/routes/query.py | 20 | 0 | 100% |
| app/services/answering.py | 57 | 0 | 100% |
| app/services/chunking.py | 41 | 0 | 100% |
| app/services/documents.py | 18 | 0 | 100% |
| app/services/embedding.py | 13 | 1 | 92% |
| app/services/retrieval.py | 11 | 0 | 100% |
| app/storage/base.py | 24 | 0 | 100% |
| app/storage/memory.py | 42 | 0 | 100% |
| **TOTAL** | **346** | **1** | **99%** |

The single uncovered line is the real `SentenceTransformer(...)` model load in
`embedding.py`, which the tests deliberately mock (determinism + no ~90 MB
download in CI). Every other application line is covered.

## Stopping the servers

```bash
lsof -t -i :8000 | xargs -r kill    # backend
lsof -t -i :5173 | xargs -r kill    # frontend
```

Windows (PowerShell):

```powershell
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 5173 | ForEach-Object { Stop-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
```

## API overview

| Method | Path            | Purpose                                                    |
| ------ | --------------- | ---------------------------------------------------------- |
| POST   | /documents      | Upload + chunk + embed a document                          |
| GET    | /documents      | List documents (id, title, chunk count, upload date)       |
| GET    | /documents/{id} | Document metadata + chunks                                 |
| DELETE | /documents/{id} | Remove a document and its data                             |
| POST   | /query          | Most relevant chunks across all documents, with scores     |
| POST   | /ask            | LLM answer grounded in retrieved chunks + the sources used |

Ready-made upload content lives in [examples/sample.md](examples/sample.md) —
paste it into POST /documents (e.g. via the /docs UI) to try the service.

## Project structure

```
├── README.md · DECISIONS.md · CODE_REVIEW.md   # setup · design record + Part 4 · Part 2 review
├── ASSESSMENT.md / ASSESSMENT.pdf              # the brief (markdown conversion + original)
├── pyproject.toml                              # ruff lint/format configuration
├── examples/sample.md                          # ready-made upload content
├── backend/
│   ├── requirements.txt · .env.example · pytest.ini
│   ├── app/
│   │   ├── main.py            # app factory: routers, exception handlers, startup model warm-up
│   │   ├── config.py          # env settings; ANTHROPIC_API_KEY present → live LLM, absent → mock
│   │   ├── errors.py          # domain exceptions + the single JSON error shape
│   │   ├── routes/            # documents.py, query.py — thin HTTP translation, zero business logic
│   │   ├── services/          # chunking, embedding, documents, retrieval, answering
│   │   ├── models/schemas.py  # every Pydantic request/response contract in one place
│   │   └── storage/           # base.py = VectorStore interface · memory.py = numpy implementation
│   └── tests/                 # pytest suite + the opt-in evaluation harness
└── frontend/
    ├── package.json           # scripts (dev/build/lint) + pinned dependencies
    ├── vite.config.ts         # dev proxy → backend, so no CORS setup is needed
    └── src/
        ├── api/               # types.ts mirrors the Pydantic schemas 1:1 · client.ts typed fetch wrapper
        └── components/        # DocumentUpload, DocumentList, QAPanel
```

The reasoning behind this layout — module responsibilities and every design
decision with its trade-offs — lives in [DECISIONS.md](DECISIONS.md)
(System Overview, Requirements Trace, and Module Map sections).

## Notes for reviewers

- **No API key needed.** Keyless, `/ask` answers via a clearly-labeled mock
  that builds the exact same prompt template as the live path; set
  `ANTHROPIC_API_KEY` in `backend/.env` to flip on live Claude answers.
- **First backend start pauses** while the ~90 MB embedding model downloads —
  one-time cost, cached afterwards.
- **Documents live in memory by design** (see DECISIONS.md, Vector storage &
  search): a backend restart clears them.
- The Q&A form stays disabled until at least one document is uploaded; if the
  backend isn't running, the UI shows a single "can't reach the backend"
  banner with a retry.

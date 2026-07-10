# Document Q&A Service — Clickatell Technical Assessment

A small document intelligence service: upload text/markdown documents, then ask
natural-language questions answered from their content. Classic RAG pipeline:
chunking → local embeddings → similarity search → grounded LLM answer with sources.

**Stack:** FastAPI · sentence-transformers (all-MiniLM-L6-v2, runs locally) ·
in-memory vector store · React + TypeScript (Vite)

**Companion docs:** [DECISIONS.md](DECISIONS.md) — architecture, every design
decision with reasoning, and Part 4 · [CODE_REVIEW.md](CODE_REVIEW.md) — Part 2

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

### Coverage report

<!-- TODO Sunday: paste the final coverage table here — the brief requires the
report in the submission, and htmlcov/ is gitignored, so this IS the report. -->

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

## Project structure

<!-- TODO Mon: short final tree here; the design reasoning lives in DECISIONS.md §§1–3 -->

## Notes for reviewers

<!-- TODO Mon: anything a grader should know before running — mock behaviour,
model download wait, how to flip live LLM on. Keep to 3–4 lines. -->

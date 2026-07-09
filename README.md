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
  runnable keyless. <!-- TODO Fri: confirm this wording matches final behaviour -->

## Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env         # add ANTHROPIC_API_KEY=... for live answers (optional)
uvicorn app.main:app --reload
```

- **First install is the slow step:** `pip install` pulls PyTorch (several
  hundred MB) as a sentence-transformers dependency — allow a few minutes.
  First _run_ then downloads the embedding model itself (~90 MB), one-time.
- Interactive API docs once running: http://localhost:8000/docs

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

<!-- TODO Mon: short final tree here; the reasoning lives in ARCHITECTURE.md -->

## Notes for reviewers

<!-- TODO Mon: anything a grader should know before running — mock behaviour,
model download wait, how to flip live LLM on. Keep to 3–4 lines. -->

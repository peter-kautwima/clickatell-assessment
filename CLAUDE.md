# Clickatell Technical Assessment — Document Q&A Service

## Context

Take-home assessment for R&D Software Engineer: Innovation (Intermediate).
Deadline: Tuesday 14 July 2026, 12:00 SAST. Full brief: ASSESSMENT.md in repo root.

## What we're building

- **FastAPI backend:** document upload → chunking → embeddings
  (sentence-transformers, all-MiniLM-L6-v2, runs locally — NO paid embedding APIs),
  in-memory vector store behind a small VectorStore interface, cosine similarity
  search, /query and /ask endpoints. /ask calls the Anthropic API for grounded
  answers; clean mock fallback (containing the real prompt template) when no API
  key is set, so the service runs keyless.
- **React + TypeScript frontend (Vite):** upload form, document list, Q&A
  interface showing the answer plus source chunks with relevance scores.
  Functional > pretty.
- Pydantic models for ALL request/response bodies. Proper HTTP status codes and
  graceful error handling throughout.

## Structure — target tree (services/ split provisional until ARCHITECTURE.md is locked)

```
clickatell-assessment/            # monorepo — one repo, one submission link
├── CLAUDE.md · ASSESSMENT.md · README.md · DECISIONS.md · ARCHITECTURE.md · CODE_REVIEW.md
├── notes/                        # gitignored, private (PLAN.md, RUBRIC.md)
├── backend/
│   ├── requirements.txt · .env.example   # .env itself is gitignored
│   ├── app/
│   │   ├── main.py               # FastAPI app factory + router registration ONLY
│   │   ├── config.py             # env settings; ANTHROPIC_API_KEY set → real LLM, absent → mock
│   │   ├── routes/               # documents.py, query.py — thin, zero business logic
│   │   ├── services/             # chunking.py, embedding.py, retrieval.py, answering.py
│   │   ├── models/schemas.py     # ALL Pydantic request/response models in one place
│   │   └── storage/              # base.py = VectorStore interface · memory.py = numpy impl
│   └── tests/                    # conftest.py (mock the embedding model in fixtures!)
│                                 # + test_documents / query / ask / chunking / storage
└── frontend/
    ├── vite.config.ts            # dev proxy → backend, avoids CORS setup
    └── src/
        ├── api/types.ts          # interfaces mirroring Pydantic schemas 1:1
        ├── api/client.ts         # typed fetch wrapper — the "no `any`" rubric line
        └── components/           # DocumentUpload.tsx, DocumentList.tsx, QAPanel.tsx
```

Routes delegate, services hold all logic. This structure is deliberately the
corrected version of the anti-pattern module in the Part 2 code review.

## Working rules (important)

1. After creating or significantly changing a module, explain it to me in plain
   English — what it does and why it's structured that way. I verify everything
   and must be able to defend every line in a verbal walkthrough.
2. Work on short-lived feature branches (feat/…, fix/…, docs/…). Merge to main
   with `--no-ff` once the feature works and is tested. Never squash.
3. Commit after each logical unit of work. Small atomic commits — the reviewers
   audit git history. Message spec (Conventional Commits):
   `type: imperative summary` (≤ ~65 chars). Types: feat, fix, test, docs,
   refactor, chore. Add a body line for the WHY only when it isn't obvious from
   the summary. One logical change per commit — if the message needs "and",
   split the commit. Examples: "feat: add cosine top-k search to memory store" ·
   "fix: return 404 for unknown document id" · "test: cover empty document upload".
4. Testing: pytest + pytest-cov, target 90%+ coverage. Write tests alongside
   features, not at the end. Cover happy paths, edge cases, and error scenarios.
   Before submission, paste the coverage table into README — htmlcov/ is
   gitignored but the brief requires a coverage report in the submission.
5. Simplicity over cleverness. Everything must be explainable, not impressive.
6. When making an architectural choice (chunk size, storage, prompt design),
   state the trade-off so I can record it in DECISIONS.md the same day, AND
   prompt me to add a matching entry to notes/WALKTHROUGH_PREP.md — every
   decision needs a defence I can speak out loud in the walkthrough.
7. Never put secrets in code. API keys via environment variables; keep
   .env.example updated with variable names only. .env is gitignored.

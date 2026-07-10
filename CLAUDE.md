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
├── CLAUDE.md · ASSESSMENT.md · README.md · DECISIONS.md · CODE_REVIEW.md
├── notes/                        # gitignored, private (PLAN.md, RUBRIC.md,
│                                 # WALKTHROUGH_PREP.md, branch-logs/)
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
   English — what it does and why it's structured that way — AND capture that
   explanation, plus the final snippet for anything non-obvious, in
   notes/branch-logs/<branch-name>.md before committing, alongside the build
   order for that branch and why it went in that order. I verify everything
   and must be able to defend every line in a verbal walkthrough — that
   explanation cannot live only in this chat.
2. main is ALWAYS runnable. Work on short-lived feature branches (feat/…,
   fix/…, docs/…). Merge to main with `--no-ff` once the feature works and is
   tested. Never squash.
3. Before the first commit of any session, verify `git config user.name` /
   `git config user.email` resolve to the real author identity, not a stale
   local override — this has silently mis-attributed an entire branch's
   commits before (WALKTHROUGH_PREP.md §12, and it recurred once already).
   If wrong, stop and tell me before committing anything; I fix git config
   myself, you never touch it. Commit after each logical unit of work. Small
   atomic commits — the reviewers audit git history. Message spec (Conventional Commits):
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
   decision needs a defence I can speak out loud in the walkthrough. Back
   every trade-off claim with the concrete evidence behind it — a number,
   benchmark, or model-card fact — not just a qualitative label like
   "conservative" or "minor." If a figure can be verified, verify and state
   it rather than asserting the conclusion alone. This applies just as much
   to trade-offs discovered mid-implementation as to ones planned upfront —
   an in-chat explanation, a branch-log entry, or a commit message is not a
   substitute for the DECISIONS.md line. Before calling a branch done,
   re-scan every commit made on it for any choice-with-a-rejected-alternative
   that isn't recorded there yet.
7. Never put secrets in code. API keys via environment variables; keep
   .env.example updated with variable names only. .env is gitignored.
8. Comments & docstrings: every module and public function gets a short
   docstring — what it does and why it exists (1–2 lines; args/returns only
   when non-obvious). Inline comments explain WHY (non-obvious choices,
   constraints like the 256-token limit), never narrate WHAT the code does.
   No commented-out code. Study notes belong in notes/WALKTHROUGH_PREP.md,
   never in source.
9. Concurrency: async endpoints for I/O-bound work using async clients
   (anthropic SDK / httpx); CPU-bound work (the embedder) runs via plain `def`
   endpoints so FastAPI's threadpool handles it. NEVER call blocking I/O
   inside `async def`. No manual threads or multiprocessing — framework-level
   concurrency only.
10. Keep collateral honest, not just DECISIONS.md/WALKTHROUGH_PREP.md: every
    requirements.txt entry gets a one-line inline comment stating why it's
    there (skip only self-evident framework glue like fastapi/uvicorn).
    README.md gets updated in the SAME commit whenever setup, run, or test
    instructions actually change — Monday's clean-clone test runs against
    what's committed, not what's remembered.

## Reference docs — when to read what

- **ASSESSMENT.md** — the exact requirements: the six endpoints, the 90%
  coverage bar, the frontend's four features. Consult it before building each
  feature and before declaring anything complete. When in doubt about a
  requirement, read it rather than assume.
- **DECISIONS.md** — the Architecture & Decision Record: system map + module
  responsibilities (§§1–4), every decision with reasoning (§5), Part 4 (§6).
  This is the design being built to — if code would deviate from §§1–5, STOP
  and flag the deviation to me before writing it. Record new trade-offs here
  the same day (rule 6).
- **README.md** — keep it true as setup evolves; Monday's clean-clone test runs off it.
- **notes/ (gitignored, still readable locally):** notes/RUBRIC.md — grading
  weights; calibrate effort to them and say so when scoping. notes/WALKTHROUGH_PREP.md —
  where rules 6 and 8 send spoken-defence entries and study notes.
  notes/branch-logs/<branch-name>.md — one file per feature branch (rule 1):
  build order + why, paired with the final non-trivial snippets and their
  plain-English explanation. This is where the module explanation from rule 1
  lands so it survives past the session that produced it — different job from
  WALKTHROUGH_PREP.md, which is concept-level defence, not code narrative.

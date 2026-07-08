# Technical Assessment — Innovation R&D Engineer (Intermediate)

> **Converted from the original PDF** (also committed to this repo as source of
> truth). Code indentation restored, page numbers removed.
> **Deadline note:** the PDF says "Monday 14 July" but 14 July 2026 is a Tuesday;
> Clickatell's email confirms **Tuesday 14 July 2026, 12:00**. Work to that.

**Candidate:** Peter Kautwima
**Position:** Research & Development Software Engineer: Innovation (Intermediate)
**Time limit:** Due by 12:00 (noon), 14 July 2026. No extensions.
**Submission:** GitHub/GitLab repository link + written responses (markdown or PDF)

---

## Before You Begin — Ground Rules

1. **Use AI tools. Seriously.** Use Claude, GitHub Copilot, ChatGPT, or any AI coding assistant to build this. That's how the team works — AI does the heavy lifting on code generation. Typing every line by hand is doing it wrong for this role.
2. **But you must be able to review and verify everything.** The job isn't writing code — it's directing AI to write code and then confirming it's correct, secure, performant, and does what you intended. They will ask you to walk through your submission and explain it. **If you can't explain it, it doesn't count.**
3. **Google, Stack Overflow, documentation — all fair game.** Not a closed-book exam.
4. **Quality over completeness.** A well-structured partial solution with clear documentation of what's missing beats a rushed complete solution with poor code quality.
5. **Show your thinking.** Include a DECISIONS.md explaining architectural choices, trade-offs, and what you'd do differently with more time. **Weighted heavily.**
6. **Commit often.** They read git history to understand the approach. Atomic commits with meaningful messages.

## How the Team Works With AI

AI operators with engineering foundations. The workflow:

1. **Direct** — tell AI what to build (requires knowing what good looks like)
2. **Generate** — let AI produce the code (the fast part)
3. **Review** — read what it produced, catch issues, understand the logic (where engineering matters)
4. **Verify** — confirm it works, handles edge cases, integrates correctly (requires real understanding)

You don't need to hand-write everything. But you DO need to understand every line well enough to catch when the AI gets it wrong — because it will. The code review section tests that directly. The follow-up conversation tests it again.

---

## The Challenge: Document Intelligence Service

A small **Document Q&A service** — users upload documents and ask natural-language questions about their content. Three parts: a **Python backend** (API service) for document processing and question answering, a **React frontend** for the UI, and a **code review** demonstrating you can read and critique Python.

---

## Part 1: Python Backend (Primary — ~45% of evaluation)

Build a FastAPI service exposing:

### Required endpoints

| Method | Path            | Purpose                                                                                                                                                                      |
| ------ | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | /documents      | Upload a text document (plain text or markdown). Store it, chunk it, generate embeddings.                                                                                    |
| GET    | /documents      | List all uploaded documents (id, title, chunk count, upload date).                                                                                                           |
| GET    | /documents/{id} | Get document metadata and its chunks.                                                                                                                                        |
| DELETE | /documents/{id} | Remove a document and its associated data.                                                                                                                                   |
| POST   | /query          | Accept a natural-language question. Find the most relevant chunks across all documents; return them with relevance scores.                                                   |
| POST   | /ask            | Accept a natural-language question. Find relevant chunks, then use an LLM to generate an answer grounded in those chunks. Return both the answer and the source chunks used. |

### Technical requirements

1. **Document chunking** — split documents into meaningful chunks (strategy and chunk size are your call — justify in DECISIONS.md).
2. **Embeddings** — generate vector embeddings per chunk using an **open-source model**: sentence-transformers (e.g. all-MiniLM-L6-v2 — recommended, local, free), any HuggingFace embedding model, or another free/open alternative. They don't care which model — they care that you understand WHY embeddings matter and HOW similarity search works. **Do NOT use paid APIs (OpenAI etc.) for embeddings.**
3. **Vector storage & search** — store embeddings, perform similarity search. In-memory (numpy cosine similarity) is perfectly acceptable; ChromaDB/FAISS/any vector library earns bonus points for reasoning about trade-offs.
4. **LLM integration (for /ask)** — call an LLM API to generate answers grounded in retrieved context. OpenAI, Anthropic, any other LLM API, **or a mock** demonstrating the prompt structure and context-injection pattern. No API keys? Mock the call but write the actual prompt template and explain the design in DECISIONS.md.
5. **Request/response models** — Pydantic models for all request and response bodies. Proper validation and error responses.
6. **Error handling** — graceful failures (invalid input, missing documents, API failures). Appropriate HTTP status codes and error messages.
7. **Project structure** — organised as for a production service: module structure, separation of concerns, dependency management.

### Evaluation (Python)

| Criteria             | Weight | What "good" looks like                                                                                                                                      |
| -------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Service architecture | High   | Clear separation of concerns (routes, services, models, storage). Not everything in one file.                                                               |
| Code quality         | High   | Readable, consistent style, meaningful names, appropriate abstractions.                                                                                     |
| Error handling       | High   | Graceful failures, proper HTTP status codes, informative error messages.                                                                                    |
| AI/RAG reasoning     | High   | Sensible chunking strategy, understanding of embeddings and similarity, good prompt design.                                                                 |
| API design           | Medium | RESTful conventions, clean request/response contracts, useful documentation.                                                                                |
| Testing              | High   | Minimum **90% code coverage**. Meaningful tests covering happy paths, edge cases, error scenarios. pytest. **Include a coverage report in the submission.** |

---

## Part 2: Code Review (Critical — ~20% of evaluation)

A Python module from an existing service, containing several issues — bugs, architectural problems, style/maintainability concerns. **Review it as a pull request from a junior developer**, in CODE_REVIEW.md. For each issue: (1) **what** the problem is (line reference or quote), (2) **why** it's a problem (bug? security? maintainability? performance?), (3) **how** you'd fix it (corrected code or approach).

**Find at least 8 distinct issues. More than 12 exist.**

### The module under review

```python
import os
import json
import requests
from fastapi import FastAPI, Request
from typing import Optional

app = FastAPI()

DATABASE_URL = "mysql://admin:password123@prod-db.internal:3306/documents"
API_KEY = "sk-proj-abc123def456"

documents = {}
counter = 0


@app.post("/upload")
async def upload_document(request: Request):
    body = await request.json()
    global counter
    counter = counter + 1
    doc = {
        "id": counter,
        "title": body["title"],
        "content": body["content"],
        "chunks": []
    }
    # chunk the document
    words = body["content"].split(" ")
    chunk_size = 100
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        doc["chunks"].append(chunk)
    # get embeddings for each chunk
    for i in range(len(doc["chunks"])):
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"input": doc["chunks"][i], "model": "text-embedding-ada-002"}
        )
        embedding = response.json()["data"][0]["embedding"]
        doc["chunks"][i] = {"text": doc["chunks"][i], "embedding": embedding}
    documents[counter] = doc
    return {"status": "ok", "id": counter}


@app.get("/search")
async def search(q: str, limit: Optional[int] = 5):
    # get query embedding
    response = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"input": q, "model": "text-embedding-ada-002"}
    )
    query_embedding = response.json()["data"][0]["embedding"]
    # find similar chunks
    results = []
    for doc_id, doc in documents.items():
        for chunk in doc["chunks"]:
            similarity = sum(a * b for a, b in zip(query_embedding, chunk["embedding"]))
            results.append({
                "doc_id": doc_id,
                "text": chunk["text"],
                "score": similarity
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


@app.post("/ask")
async def ask_question(request: Request):
    body = await request.json()
    question = body["question"]
    search_results = await search(question)
    context = ""
    for r in search_results:
        context += r["text"] + "\n\n"
    prompt = f"Answer this question: {question}\n\nContext: {context}"
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    answer = response.json()["choices"][0]["message"]["content"]
    return {"answer": answer}


@app.delete("/documents/{id}")
async def delete_document(id):
    del documents[id]
    return {"status": "deleted"}


@app.get("/documents")
async def list_documents():
    return documents
```

### Evaluation (Code Review)

| Criteria             | Weight | What "good" looks like                                                             |
| -------------------- | ------ | ---------------------------------------------------------------------------------- |
| Issue identification | High   | Catches security, correctness, and architectural issues — not just style nitpicks. |
| Explanation quality  | High   | Articulates WHY something is wrong, not just that it "looks bad."                  |
| Fix quality          | Medium | Proposed fixes are correct and demonstrate understanding of the language.          |
| Prioritisation       | Medium | Distinguishes critical issues (security, bugs) from nice-to-haves (style).         |

---

## Part 3: React Frontend (Secondary — ~15% of evaluation)

A simple React/TypeScript frontend against the backend:

1. **Document upload** — form/interface to paste or upload text content with a title.
2. **Document list** — uploaded documents with metadata.
3. **Q&A interface** — chat-like: type a question, see the AI answer, see the source chunks that informed it (with relevance scores).
4. **Loading/error states** — handle async operations gracefully.

### Evaluation (React)

| Criteria               | Weight | What "good" looks like                                                               |
| ---------------------- | ------ | ------------------------------------------------------------------------------------ |
| Component architecture | Medium | Logical breakdown, separation of concerns, reusable where appropriate.               |
| TypeScript usage       | Medium | Proper typing (not `any` everywhere), interfaces for API responses, type-safe props. |
| State management       | Low    | Appropriate for the scale — hooks/context fine. No Redux needed.                     |
| UX                     | Low    | Functional and clear. Design skills not evaluated — basic usability only.            |

Notes: any React setup (Vite, CRA, Next.js). Styling not important — functional > pretty. This section should be fast; don't over-engineer.

---

## Part 4: Architecture & Reasoning (Written — ~20% of evaluation)

Answer in DECISIONS.md (or separate ARCHITECTURE.md):

### 4.1 — Production readiness

For 1,000 documents and 100 concurrent users: what changes in your implementation? How do you handle embedding generation at scale (slow and expensive)? What production storage and why?

### 4.2 — Deployment

Briefly, deploying to AWS: which AWS services? How do you handle the Python backend vs the React frontend? What about the vector store / embedding model? (They don't expect deep AWS expertise — they want to see how you think about deployment.)

### 4.3 — Guardrails & safety

For /ask in production: how do you prevent the LLM answering questions NOT grounded in the uploaded documents (hallucination)? How do you handle potentially harmful or off-topic queries? What do you monitor to ensure the system works correctly?

### 4.4 — Your approach

How did you approach this assessment; what did you learn? Where did AI tools help most; where did you rely on your own understanding? Hardest part and how you worked through it? What would you build differently with 2 more days?

---

## Bonus (Optional — shows initiative)

Pick ONE (or none — genuinely optional):

- **Conversation memory** — /ask supports follow-ups referencing previous answers.
- **Streaming responses** — stream the LLM response token-by-token to the frontend.
- **Document format support** — handle PDF upload (extract text) in addition to plain text.
- **Evaluation harness** — a simple test measuring answer quality (known Q&A pairs → does the system return correct answers?).

---

## Submission Checklist

- [ ] Git repository with meaningful commit history
- [ ] README.md with setup instructions (runnable locally)
- [ ] DECISIONS.md covering Part 4 + architectural choices throughout
- [ ] CODE_REVIEW.md with the Part 2 review
- [ ] Working Python backend (even if LLM call is mocked)
- [ ] Working React frontend communicating with the backend
- [ ] Test suite with ≥90% code coverage (pytest + coverage report included)
- [ ] requirements.txt or pyproject.toml
- [ ] package.json for frontend dependencies

## What They're NOT Testing

Memorised stdlib or obscure language features · deep NLP theory or citing papers · AWS certification-level infrastructure knowledge · design/CSS skills · speed (a week — take the time to do it well).

## What They ARE Testing

- Can you **direct AI effectively** to build a structured, production-quality Python service in a domain that's new to you?
- Can you **review and verify** what AI produces — catching bugs, security issues, and architectural flaws in Python?
- Do you understand how AI/LLM features work architecturally (**RAG, embeddings, context injection**)?
- Can you **explain every decision** in your codebase — why it's there, what it does, what could go wrong?
- Is the output **clean, well-reasoned, maintainable** — regardless of who (or what) wrote it?
- Can you articulate **trade-offs, decisions, and growth areas honestly**?

## Follow-Up

They reserve the right to schedule a **30-minute technical walkthrough**: (1) walk through your architecture and key decisions, (2) explain specific code sections **they** select, (3) discuss what you'd change and how you'd extend the system, (4) answer questions about your code review findings. The submission should stand on its own — but be prepared to defend it verbally.

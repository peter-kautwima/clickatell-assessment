# DECISIONS.md

> Architectural choices, trade-offs, and reasoning for the Document Q&A service.
> Each section is filled in on the day the decision is made — not reconstructed
> at the end.

## Chunking strategy

<!-- Fill Thu: strategy, chunk size, overlap, why; alternatives rejected and why -->

## Embedding model

<!-- Fill Thu: all-MiniLM-L6-v2 — why this one; dimensions, speed, quality trade-offs -->

## Vector storage & search

<!-- Fill Thu: in-memory behind a VectorStore interface; cosine similarity; trade-offs
vs ChromaDB/FAISS; what the production swap looks like and why the interface makes it cheap -->

## LLM integration & prompt design

<!-- Fill Fri: prompt template, context injection pattern, grounding instructions,
why the mock fallback is designed the way it is -->

## Error handling approach

<!-- Fill Fri: status code conventions, validation strategy, failure modes covered -->

## Testing approach

<!-- Fill Fri: what's tested and why, how the embedding model is mocked in tests,
coverage figure + where the report lives -->

---

# Part 4 — Architecture & Reasoning

## 4.1 Production readiness

<!-- Fill Sun: what changes at 1,000 docs / 100 concurrent users; embedding
generation at scale; production storage choice and why -->

## 4.2 Deployment (AWS)

<!-- Fill Sun: services for backend vs frontend; where the vector store and
embedding model live; keep it a sketch, not a certification exam -->

## 4.3 Guardrails & safety

<!-- Fill Sun: grounding / hallucination prevention on /ask; harmful and
off-topic query handling; what I'd monitor and why -->

## 4.4 My approach

<!-- Fill Sun/Mon, honestly: how I worked, where AI helped most vs where my own
judgment was required, hardest part and how I got through it, what I'd build
differently with 2 more days -->

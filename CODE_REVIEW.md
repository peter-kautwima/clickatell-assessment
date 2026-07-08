# CODE_REVIEW.md — Review of the Provided Module (Part 2)

> Reviewed as a pull request from a junior developer. Issues are ordered by
> severity — **Critical** (security / correctness / data loss) → **High**
> (bugs, architectural problems) → **Medium** (robustness, performance) →
> **Low** (style, maintainability) — because prioritisation is explicitly
> part of the rubric. Each issue: **what** (with the offending code) →
> **why it matters** → **the fix**.

## Summary

<!-- TODO (write LAST, after all issues are in): 3–4 sentences — overall
assessment, the recurring themes (e.g. secrets in code, blocking I/O inside
async endpoints, no input validation, global mutable state, missing error
handling), and what I'd ask the author to fix before this could merge. -->

---

## Critical

### C1. <!-- Issue title -->

**What:**

```python
# offending line(s), quoted from the module
```

**Why it matters:** <!-- security breach / crash / data loss — the concrete consequence -->
**Fix:**

```python
# corrected code, or the approach if the fix is structural
```

<!-- Repeat the template per issue: C2, C3... then H1..., M1..., L1... -->

## High

## Medium

## Low

---

## What I'd say to the author

<!-- TODO: 2–3 sentences of genuine mentoring tone — what they did reasonably,
what pattern to study next. The brief says "as if from a junior developer";
a review that teaches rather than just corrects is part of the demonstration. -->

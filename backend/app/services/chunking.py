"""Structure-aware document chunking: paragraph-first, merged toward a target
size, with overlap-windowed splitting as the fallback for oversized paragraphs.

Chunk size and overlap rationale: DECISIONS.md D1 (Chunking).
"""

from __future__ import annotations

import re

# These are word counts, used as a proxy for the model's 256-token ceiling.
# Counting words keeps chunking a pure function with no tokenizer dependency,
# at the cost of being an approximation (~1.3-1.4 tokens per English word).
TARGET_WORDS = 180
MAX_CHUNK_WORDS = 256
OVERLAP_WORDS = 30

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = _PARAGRAPH_SPLIT.split(text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _split_oversized_paragraph(words: list[str]) -> list[str]:
    """Slide a MAX_CHUNK_WORDS window over an oversized paragraph, stepping by
    (MAX_CHUNK_WORDS - OVERLAP_WORDS) so consecutive windows share ~OVERLAP_WORDS
    words — the only place overlap applies.
    """
    step = MAX_CHUNK_WORDS - OVERLAP_WORDS
    windows = []
    for start in range(0, len(words), step):
        window = words[start : start + MAX_CHUNK_WORDS]
        windows.append(" ".join(window))
        if start + MAX_CHUNK_WORDS >= len(words):
            break
    return windows


def chunk_text(text: str) -> list[str]:
    """Split text into structure-aware chunks: whole paragraphs merged toward
    TARGET_WORDS, capped at MAX_CHUNK_WORDS, with overlap-windowed splitting
    for any single paragraph that alone exceeds the cap.
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer_words: list[str] = []

    def flush() -> None:
        if buffer_words:
            chunks.append(" ".join(buffer_words))
            buffer_words.clear()

    for paragraph in paragraphs:
        paragraph_words = paragraph.split()

        if len(paragraph_words) > MAX_CHUNK_WORDS:
            flush()
            chunks.extend(_split_oversized_paragraph(paragraph_words))
            continue

        exceeds_cap = len(buffer_words) + len(paragraph_words) > MAX_CHUNK_WORDS
        reached_target = len(buffer_words) >= TARGET_WORDS
        if exceeds_cap or reached_target:
            flush()

        buffer_words.extend(paragraph_words)

    flush()
    return chunks

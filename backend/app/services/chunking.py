"""Structure-aware document chunking (D1): paragraph-first, merged toward a
target size, with overlap-windowed splitting as the fallback for oversized
paragraphs. See DECISIONS.md D1 for the full rationale.
"""

from __future__ import annotations

import re
from typing import List

# Word count is used as a proxy for the model's 256-word-piece ceiling: chunk_text
# stays a pure function with no tokenizer/model dependency (see module map), at the
# cost of being an approximation — see DECISIONS.md D1 addendum.
TARGET_WORDS = 180
MAX_CHUNK_WORDS = 256
OVERLAP_WORDS = 30

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


def _split_paragraphs(text: str) -> List[str]:
    paragraphs = _PARAGRAPH_SPLIT.split(text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _split_oversized_paragraph(words: List[str]) -> List[str]:
    """Slide a MAX_CHUNK_WORDS window over an oversized paragraph, stepping by
    (MAX_CHUNK_WORDS - OVERLAP_WORDS) so consecutive windows share ~OVERLAP_WORDS
    words — the only place overlap applies (D1).
    """
    step = MAX_CHUNK_WORDS - OVERLAP_WORDS
    windows = []
    for start in range(0, len(words), step):
        window = words[start : start + MAX_CHUNK_WORDS]
        windows.append(" ".join(window))
        if start + MAX_CHUNK_WORDS >= len(words):
            break
    return windows


def chunk_text(text: str) -> List[str]:
    """Split text into structure-aware chunks: whole paragraphs merged toward
    TARGET_WORDS, capped at MAX_CHUNK_WORDS, with overlap-windowed splitting
    for any single paragraph that alone exceeds the cap.
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    chunks: List[str] = []
    buffer_words: List[str] = []

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

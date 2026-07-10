from app.services.chunking import (
    MAX_CHUNK_WORDS,
    OVERLAP_WORDS,
    TARGET_WORDS,
    chunk_text,
)


def _words(n: int, prefix: str = "word") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_single_short_paragraph_returns_one_chunk():
    text = "This is a short paragraph."
    assert chunk_text(text) == [text]


def test_small_paragraphs_merge_until_target_then_split_on_cap():
    # Two 100-word paragraphs merge (200 <= cap), a third would exceed the
    # 256-word cap so it starts a fresh chunk instead.
    p1, p2, p3 = _words(100, "a"), _words(100, "b"), _words(100, "c")
    text = f"{p1}\n\n{p2}\n\n{p3}"

    chunks = chunk_text(text)

    assert len(chunks) == 2
    assert chunks[0] == f"{p1} {p2}"
    assert chunks[1] == p3


def test_buffer_flushes_once_target_reached_even_under_cap():
    # A paragraph alone at/above TARGET_WORDS flushes before the next
    # paragraph is merged in, even though the two together would still
    # fit under MAX_CHUNK_WORDS.
    p1 = _words(TARGET_WORDS + 10, "a")
    p2 = _words(50, "b")
    text = f"{p1}\n\n{p2}"

    chunks = chunk_text(text)

    assert chunks == [p1, p2]


def test_oversized_paragraph_splits_into_overlapping_windows():
    words = [f"w{i}" for i in range(300)]
    text = " ".join(words)

    chunks = chunk_text(text)

    assert len(chunks) == 2
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert len(first_words) == MAX_CHUNK_WORDS
    assert first_words == words[:MAX_CHUNK_WORDS]
    assert second_words == words[MAX_CHUNK_WORDS - OVERLAP_WORDS :]
    # The overlap window: the last OVERLAP_WORDS of chunk 1 repeat as the
    # first OVERLAP_WORDS of chunk 2 (D1's insurance against severed ideas).
    assert first_words[-OVERLAP_WORDS:] == second_words[:OVERLAP_WORDS]


def test_paragraph_at_exactly_the_ceiling_stays_whole():
    text = _words(MAX_CHUNK_WORDS)

    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_paragraph_one_word_over_the_ceiling_gets_split():
    text = _words(MAX_CHUNK_WORDS + 1)

    chunks = chunk_text(text)

    assert len(chunks) == 2
    assert len(chunks[0].split()) == MAX_CHUNK_WORDS

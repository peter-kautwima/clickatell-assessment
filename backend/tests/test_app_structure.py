from app.services.chunking import chunk_text


def test_chunking_returns_list():
    chunks = chunk_text("hello world", chunk_size=5)
    assert isinstance(chunks, list)

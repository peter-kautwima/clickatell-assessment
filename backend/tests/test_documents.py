def _upload(client, title="Test Doc", content="Some content here."):
    return client.post("/documents", json={"title": title, "content": content})


def _long_two_chunk_content() -> str:
    # Two 150-word paragraphs: together they exceed chunking's 256-word cap,
    # so chunk_text yields exactly two chunks — a known, assertable count.
    paragraph_one = " ".join(f"alpha{i}" for i in range(150))
    paragraph_two = " ".join(f"beta{i}" for i in range(150))
    return f"{paragraph_one}\n\n{paragraph_two}"


def test_upload_returns_201_with_the_briefs_metadata_fields(client):
    response = _upload(client, content="One short paragraph.")

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["title"] == "Test Doc"
    assert body["chunk_count"] == 1
    assert body["created_at"]


def test_upload_chunk_count_reflects_real_chunking(client):
    response = _upload(client, content=_long_two_chunk_content())

    assert response.status_code == 201
    assert response.json()["chunk_count"] == 2


def test_full_lifecycle_upload_list_get_delete(client):
    doc_id = _upload(client, title="Lifecycle").json()["id"]

    listed = client.get("/documents").json()["documents"]
    assert [d["id"] for d in listed] == [doc_id]
    assert listed[0]["title"] == "Lifecycle"

    detail = client.get(f"/documents/{doc_id}").json()
    assert detail["id"] == doc_id
    assert detail["chunks"] == ["Some content here."]
    assert detail["chunk_count"] == len(detail["chunks"])

    delete_response = client.delete(f"/documents/{doc_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.get("/documents").json()["documents"] == []


def test_get_unknown_id_returns_404_with_d5_error_shape(client):
    response = client.get("/documents/no-such-id")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "document_not_found"
    assert "no-such-id" in body["error"]["message"]


def test_delete_unknown_id_returns_404(client):
    response = client.delete("/documents/no-such-id")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


def test_empty_content_returns_400_not_422(client):
    response = _upload(client, content="")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_document"


def test_whitespace_only_content_returns_400(client):
    response = _upload(client, content="   \n\n\t  ")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_document"


def test_missing_fields_return_422(client):
    assert client.post("/documents", json={}).status_code == 422
    assert client.post("/documents", json={"title": "No content"}).status_code == 422


def test_empty_title_returns_422(client):
    # Title emptiness IS a shape error (min_length=1), unlike content
    # emptiness which is semantic — the D5 422-vs-400 line, tested from
    # both sides.
    response = _upload(client, title="", content="Real content.")

    assert response.status_code == 422

def _upload(client, title: str, content: str) -> str:
    response = client.post("/documents", json={"title": title, "content": content})
    assert response.status_code == 201
    return response.json()["id"]


def test_query_returns_ranked_chunks_across_documents_and_respects_k(client):
    first_id = _upload(client, "First", "alpha target phrase")
    second_id = _upload(client, "Second", "alpha target other")
    _upload(client, "Third", "beta supporting phrase")

    response = client.post("/query", json={"question": "alpha target phrase", "k": 2})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["document_id"] == first_id
    assert {result["document_id"] for result in results} == {first_id, second_id}
    assert [result["score"] for result in results] == sorted(
        [result["score"] for result in results], reverse=True
    )
    assert results[0]["chunk"] == "alpha target phrase"


def test_query_uses_default_k_of_five(client):
    for index in range(6):
        _upload(client, f"Doc {index}", f"content number {index}")

    response = client.post("/query", json={"question": "content"})

    assert response.status_code == 200
    assert len(response.json()["results"]) == 5


def test_query_k_larger_than_store_returns_available_chunks(client):
    _upload(client, "Only", "one searchable chunk")

    response = client.post("/query", json={"question": "anything", "k": 10})

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def test_query_rejects_k_outside_bounds(client):
    assert client.post("/query", json={"question": "valid", "k": 0}).status_code == 422
    assert client.post("/query", json={"question": "valid", "k": 11}).status_code == 422


def test_empty_question_returns_400_with_d5_error_shape(client):
    response = client.post("/query", json={"question": "   \n\t  "})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_question"


def test_missing_question_returns_422(client):
    response = client.post("/query", json={})

    assert response.status_code == 422


def test_query_empty_store_returns_200_empty_results(client):
    response = client.post("/query", json={"question": "anything"})

    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_query_embeds_question_through_same_mocked_model(client, mock_embedding_model):
    _upload(client, "Doc", "stored text")

    response = client.post("/query", json={"question": "stored text", "k": 1})

    assert response.status_code == 200
    assert mock_embedding_model.calls[-1] == ["stored text"]

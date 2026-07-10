from app.main import app
from app.services import documents as documents_service
from app.services import embedding
from fastapi.testclient import TestClient


def test_startup_warms_the_mocked_embedding_model(mock_embedding_model):
    """Guards the from-import monkeypatch gotcha: if main.py imported
    `_get_model` by name instead of going through the `embedding` module,
    this would try to load the real model instead of the mock.
    """
    with TestClient(app):
        pass

    assert embedding._get_model() is mock_embedding_model


def test_root_liveness_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "message" in response.json()


def test_unexpected_error_returns_500_in_d5_shape_without_leaking(monkeypatch):
    def boom(store):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(documents_service, "list_documents", boom)

    # raise_server_exceptions=False: let the app's own handler answer
    # instead of the TestClient re-raising into the test.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/documents")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "secret internal detail" not in body["error"]["message"]

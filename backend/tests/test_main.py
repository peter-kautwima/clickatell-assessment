from app.main import app
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

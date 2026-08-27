from starlette.testclient import TestClient

from src.web.main import app


def test_index_returns_html():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "<html" in response.text.lower()
        assert "cdn.jsdelivr.net/npm/d3@7" in response.text


def test_api_graph_structure():
    with TestClient(app) as client:
        response = client.get("/api/graph")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert isinstance(data.get("nodes"), list)
        assert "edges" in data

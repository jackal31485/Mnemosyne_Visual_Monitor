import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_profiles_diag():
    response = client.get("/profiles/diag")
    assert response.status_code == 200
    data = response.json()
    # Basic structure checks
    assert "total_profiles" in data
    assert "total_memories" in data
    assert "profiles" in data
    assert isinstance(data["profiles"], list)
    for p in data["profiles"]:
        assert set(p.keys()) == {"id", "name", "memory_count"}

def test_graph_diag():
    response = client.get("/graph/diag")
    assert response.status_code == 200
    data = response.json()
    assert "node_count" in data and isinstance(data["node_count"], int)
    assert "edge_count" in data and isinstance(data["edge_count"], int)

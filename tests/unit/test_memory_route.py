from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.routes import memories


def test_memory_content_route_uses_distributed_gateway(monkeypatch):
    calls = []

    class FakeGateway:
        def get_memory(self, profile, memory_id):
            calls.append(("content", profile, memory_id))
            return "remote source memory"

        def get_memory_metadata(self, profile, memory_id):
            calls.append(("metadata", profile, memory_id))
            return {
                "event_date": "2026-09-26",
                "event_date_precision": "day",
                "timestamp": "2026-09-26T12:00:00",
                "created_at": "2026-09-26T12:00:00",
            }

    monkeypatch.setattr(
        memories,
        "DistributedMemoryGateway",
        FakeGateway,
    )

    client = TestClient(app)

    response = client.get(
        "/api/memories/"
        "agent-a%3Aathena/"
        "memory-1"
    )

    assert response.status_code == 200
    assert response.json() == {
        "profile": "agent-a:athena",
        "memory_id": "memory-1",
        "content": "remote source memory",
        "event_date": "2026-09-26",
        "event_date_precision": "day",
        "timestamp": "2026-09-26T12:00:00",
        "created_at": "2026-09-26T12:00:00",
    }

    assert calls == [
        ("content", "agent-a:athena", "memory-1"),
        ("metadata", "agent-a:athena", "memory-1"),
    ]


def test_memory_content_route_returns_404_for_missing_source(monkeypatch):
    class FakeGateway:
        def get_memory(self, profile, memory_id):
            raise KeyError(
                f"Memory {memory_id} not found for profile {profile}"
            )

        def get_memory_metadata(self, profile, memory_id):
            raise AssertionError(
                "Metadata must not be requested after content failure"
            )

    monkeypatch.setattr(
        memories,
        "DistributedMemoryGateway",
        FakeGateway,
    )

    client = TestClient(app)

    response = client.get(
        "/api/memories/"
        "agent-a%3Aathena/"
        "missing-memory"
    )

    assert response.status_code == 404
    assert "missing-memory" in response.json()["detail"]

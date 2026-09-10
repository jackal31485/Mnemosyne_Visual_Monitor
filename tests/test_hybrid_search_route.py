from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.routes.search import hybrid_service_dep
from src.retrieval.hybrid_search import HybridResult


class FakeService:
    reranker = object()

    def __init__(self):
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return [
            HybridResult(
                entry_id=7,
                source_profile="athena",
                origin_memory_id="memory-7",
                fused_score=0.12,
                fused_rank=1,
                reranker_score=0.91,
                reranker_rank=1,
                rank_change=0,
                keyword_rank=1,
                keyword_contribution=1 / 61,
                semantic_rank=2,
                semantic_contribution=1 / 62,
                graph_rank=None,
                graph_contribution=0.0,
                temporal_rank=None,
                temporal_contribution=0.0,
                provenance=[{"source_profile": "athena", "origin_memory_id": "memory-7"}],
            )
        ]


def test_hybrid_route_delegates_and_serializes():
    service = FakeService()
    app.dependency_overrides[hybrid_service_dep] = lambda: service
    try:
        client = TestClient(app)
        response = client.get(
            "/api/search/hybrid",
            params={
                "q": "timeline repair",
                "top_k": 5,
                "candidate_limit": 20,
                "profile": "athena",
                "rerank": "true",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "timeline repair"
    assert body["profile"] == "athena"
    assert body["reranker_available"] is True
    assert body["results"][0]["entry_id"] == 7
    assert body["results"][0]["keyword_rank"] == 1
    assert service.calls[0][0] == "timeline repair"
    assert service.calls[0][1]["profile"] == "3de1e96e-70e5-49e0-a128-529c55071b2b:athena"


def test_hybrid_route_maps_date_filters_to_event_date_mode():
    service = FakeService()
    app.dependency_overrides[hybrid_service_dep] = lambda: service
    try:
        client = TestClient(app)
        response = client.get(
            "/api/search/hybrid",
            params={
                "q": "phase 7",
                "date_from": "2026-09-01",
                "date_to": "2026-09-07",
                "rerank": "false",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["temporal_mode"] == "event_date"
    assert service.calls[0][1]["temporal_mode"] == "event_date"
    assert service.calls[0][1]["temporal_start"] == datetime(2026, 9, 1)
    assert service.calls[0][1]["temporal_end"].date().isoformat() == "2026-09-07"
    assert service.calls[0][1]["rerank"] is False


def test_hybrid_route_rejects_partial_date_window():
    service = FakeService()
    app.dependency_overrides[hybrid_service_dep] = lambda: service
    try:
        client = TestClient(app)
        response = client.get(
            "/api/search/hybrid",
            params={"q": "phase 7", "date_from": "2026-09-01"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "must be supplied together" in response.json()["detail"]

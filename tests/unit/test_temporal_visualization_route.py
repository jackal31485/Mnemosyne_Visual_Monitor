from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.temporal_visualization import router


def _client() -> TestClient:
    application = FastAPI()
    application.include_router(router)
    return TestClient(application)


def test_entity_temporal_visualization_returns_html():
    client = _client()

    response = client.get(
        "/api/temporal/history/visualization/entity/test-entity"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Temporal history" in response.text
    assert "Evidence boundary" in response.text
    assert "Missing temporal evidence" in response.text
    assert "Timeline" in response.text


def test_relationship_temporal_visualization_returns_html():
    client = _client()

    response = client.get(
        "/api/temporal/history/visualization/relationship",
        params={
            "source_entity_id": "source",
            "target_entity_id": "target",
            "relation": "works_with",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Temporal history" in response.text
    assert "works_with" in response.text
    assert "Evidence boundary" in response.text
    assert "Missing temporal evidence" in response.text


def test_relationship_visualization_requires_relationship_parameters():
    client = _client()

    response = client.get(
        "/api/temporal/history/visualization/relationship"
    )

    assert response.status_code == 422

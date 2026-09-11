from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.routes.entity_graph import entity_graph_service_dep
from domain.collective import CollectiveDAO
from domain.entities import EntityDAO
from domain.entity_mentions import EntityMentionDAO
from domain.entity_resolutions import EntityResolutionDAO
from domain.relationships import RelationshipDAO
from services.entity_graph_service import EntityGraphService


def _build_service(db_path: Path) -> EntityGraphService:
    collective = CollectiveDAO(db_path)
    entities = EntityDAO(db_path)
    mentions = EntityMentionDAO(db_path)
    resolutions = EntityResolutionDAO(db_path)
    relationships = RelationshipDAO(db_path)

    collective.ensure_schema()
    entities.ensure_schema()
    mentions.ensure_schema()
    resolutions.ensure_schema()
    relationships.ensure_schema()

    return EntityGraphService(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        relationship_dao=relationships,
    )


def test_entity_graph_endpoint_returns_expected_shape(tmp_path: Path) -> None:
    service = _build_service(tmp_path / "collective.db")

    application = create_app()
    application.dependency_overrides[entity_graph_service_dep] = lambda: service

    try:
        client = TestClient(application)
        response = client.get("/api/entity-graph")

        assert response.status_code == 200
        payload = response.json()

        assert set(payload) == {"nodes", "edges"}
        assert isinstance(payload["nodes"], list)
        assert isinstance(payload["edges"], list)
    finally:
        application.dependency_overrides.clear()


def test_entity_graph_endpoint_is_read_only(tmp_path: Path) -> None:
    db_path = tmp_path / "collective.db"
    service = _build_service(db_path)

    application = create_app()
    application.dependency_overrides[entity_graph_service_dep] = lambda: service

    try:
        before = db_path.read_bytes()

        client = TestClient(application)
        response = client.get("/api/entity-graph")

        after = db_path.read_bytes()

        assert response.status_code == 200
        assert before == after
    finally:
        application.dependency_overrides.clear()


def test_existing_graph_endpoint_remains_registered(tmp_path: Path) -> None:
    service = _build_service(tmp_path / "collective.db")

    application = create_app()
    application.dependency_overrides[entity_graph_service_dep] = lambda: service

    try:
        paths = {
            route.path
            for route in application.routes
            if hasattr(route, "path")
        }

        assert "/api/graph" in paths
        assert "/api/entity-graph" in paths
    finally:
        application.dependency_overrides.clear()

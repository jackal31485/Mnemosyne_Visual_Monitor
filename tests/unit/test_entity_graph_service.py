from pathlib import Path

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


def test_entity_graph_service_returns_projected_graph(tmp_path: Path) -> None:
    service = _build_service(tmp_path / "collective.db")

    graph = service.get_graph()

    assert set(graph) == {"nodes", "edges"}
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)


def test_entity_graph_service_is_read_only_projection(tmp_path: Path) -> None:
    db_path = tmp_path / "collective.db"
    service = _build_service(db_path)

    before = db_path.read_bytes()
    first = service.get_graph()
    after = db_path.read_bytes()

    second = service.get_graph()

    assert before == after
    assert first == second


def test_entity_graph_service_does_not_expose_memory_content(
    tmp_path: Path,
) -> None:
    service = _build_service(tmp_path / "collective.db")

    graph = service.get_graph()

    serialized = repr(graph).lower()

    assert "content" not in serialized
    assert "raw_text" not in serialized
    assert "memory_text" not in serialized

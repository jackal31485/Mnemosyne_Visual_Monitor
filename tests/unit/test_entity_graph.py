"""Focused tests for the Phase 10G.1 entity graph projection."""

from __future__ import annotations

import numpy as np
import pytest

from domain.collective import CollectiveDAO
from domain.entities import EntityDAO
from domain.entity_graph import EntityGraphProjector
from domain.entity_mentions import EntityMentionDAO
from domain.entity_resolutions import EntityResolutionDAO
from domain.relationships import RelationshipDAO


@pytest.fixture
def graph_daos(tmp_path):
    collective = CollectiveDAO(tmp_path / "collective.db")
    entities = EntityDAO(tmp_path / "collective.db")
    mentions = EntityMentionDAO(tmp_path / "collective.db")
    resolutions = EntityResolutionDAO(tmp_path / "collective.db")
    relationships = RelationshipDAO(tmp_path / "collective.db")

    collective.ensure_schema()
    entities.ensure_schema()
    mentions.ensure_schema()
    resolutions.ensure_schema()
    relationships.ensure_schema()

    yield collective, entities, mentions, resolutions, relationships

    collective.close()
    entities.close()
    mentions.close()
    resolutions.close()
    relationships.close()


def _promote(dao, profile: str, memory_id: str) -> int:
    entry_id = dao.insert_collective_entry(
        source_profile=profile,
        origin_memory_id=memory_id,
    )
    dao.update_entry_promoted(entry_id)
    return entry_id


def _project(graph_daos):
    collective, entities, mentions, resolutions, relationships = graph_daos
    return EntityGraphProjector(
        collective,
        entities,
        mentions,
        resolutions,
        relationships,
    )


def test_projects_promoted_memory_and_resolved_entity(graph_daos):
    collective, entities, mentions, resolutions, _ = graph_daos

    entry_id = _promote(collective, "athena", "mem-1")
    entity_id = entities.create("Python", "technology")

    mention_id = mentions.add(
        collective_entry_id=entry_id,
        source_memory_id="mem-1",
        source_profile="athena",
        mention_text="Python",
        entity_type="technology",
        extraction_method="deterministic-v1",
        confidence=0.95,
    )

    resolutions.create(
        mention_id=mention_id,
        decision="same_entity",
        proposed_entity_id=entity_id,
        confidence=1.0,
        resolution_method="normalized-name-v1",
    )

    nodes, edges = _project(graph_daos).build()

    assert {
        (node.node_type, node.node_id)
        for node in nodes
    } == {
        ("memory", f"memory:collective:{entry_id}"),
        ("entity", f"entity:{entity_id}"),
    }

    assert len(edges) == 1
    assert edges[0].edge_type == "mentions"
    assert edges[0].collective_entry_id == entry_id
    assert edges[0].source_id == f"memory:collective:{entry_id}"
    assert edges[0].target_id == f"entity:{entity_id}"


def test_duplicate_origin_memory_ids_do_not_collapse(graph_daos):
    collective, _, _, _, _ = graph_daos

    first = _promote(collective, "athena", "same-memory")
    second = _promote(collective, "odin", "same-memory")

    nodes, edges = _project(graph_daos).build()

    memory_nodes = [
        node for node in nodes
        if node.node_type == "memory"
    ]

    assert len(memory_nodes) == 2
    assert {
        node.node_id for node in memory_nodes
    } == {
        f"memory:collective:{first}",
        f"memory:collective:{second}",
    }
    assert edges == []


def test_unpromoted_and_revoked_entries_are_excluded(graph_daos):
    collective, entities, mentions, resolutions, _ = graph_daos

    promoted = _promote(collective, "athena", "promoted")
    unpromoted = collective.insert_collective_entry(
        source_profile="athena",
        origin_memory_id="unpromoted",
    )
    revoked = _promote(collective, "athena", "revoked")
    collective.update_entry_revoked(revoked, "test")

    entity_id = entities.create("Python", "technology")

    for entry_id, memory_id in (
        (promoted, "promoted"),
        (unpromoted, "unpromoted"),
        (revoked, "revoked"),
    ):
        mention_id = mentions.add(
            collective_entry_id=entry_id,
            source_memory_id=memory_id,
            source_profile="athena",
            mention_text="Python",
            entity_type="technology",
            extraction_method="deterministic-v1",
            confidence=0.95,
        )
        resolutions.create(
            mention_id=mention_id,
            decision="same_entity",
            proposed_entity_id=entity_id,
            confidence=1.0,
            resolution_method="normalized-name-v1",
        )

    nodes, edges = _project(graph_daos).build()

    assert [
        node.node_id
        for node in nodes
        if node.node_type == "memory"
    ] == [f"memory:collective:{promoted}"]

    assert len(edges) == 1
    assert edges[0].collective_entry_id == promoted


@pytest.mark.parametrize(
    "decision",
    ["unresolved", "new_entity", "ambiguous", "rejected"],
)
def test_non_same_entity_resolutions_do_not_create_mentions(
    graph_daos,
    decision,
):
    collective, entities, mentions, resolutions, _ = graph_daos

    entry_id = _promote(collective, "athena", "mem-1")
    entity_id = entities.create("Python", "technology")

    mention_id = mentions.add(
        collective_entry_id=entry_id,
        source_memory_id="mem-1",
        source_profile="athena",
        mention_text="Python",
        entity_type="technology",
        extraction_method="deterministic-v1",
        confidence=0.95,
    )

    resolutions.create(
        mention_id=mention_id,
        decision=decision,
        proposed_entity_id=entity_id if decision != "unresolved" else None,
        confidence=1.0 if decision == "new_entity" else 0.0,
        resolution_method="normalized-name-v1",
    )

    nodes, edges = _project(graph_daos).build()

    assert [node for node in nodes if node.node_type == "entity"] == []
    assert edges == []


def test_relationship_projection_preserves_kind_and_lifecycle(graph_daos):
    collective, entities, _, _, relationships = graph_daos

    _promote(collective, "athena", "mem-1")

    subject = entities.create("Hermes", "project")
    object_id = entities.create("Mnemosyne", "project")

    relationship_id = relationships.create(
        subject,
        "uses",
        object_id,
        confidence=0.9,
        relationship_kind="explicit",
    )

    nodes, edges = _project(graph_daos).build()

    assert {
        node.node_id for node in nodes
    } == {
        f"entity:{subject}",
        f"entity:{object_id}",
        "memory:collective:1",
    }

    relationship_edges = [
        edge for edge in edges
        if edge.relationship_id == relationship_id
    ]

    assert len(relationship_edges) == 1
    assert relationship_edges[0].edge_type == "uses"
    assert relationship_edges[0].relationship_kind == "explicit"
    assert relationship_edges[0].confidence == 0.9


def test_inferred_relationship_remains_inferred(graph_daos):
    _, entities, _, _, relationships = graph_daos

    subject = entities.create("Athena", "agent")
    object_id = entities.create("Hermes", "project")

    relationship_id = relationships.create(
        subject,
        "associated_with",
        object_id,
        confidence=0.7,
        relationship_kind="inferred",
    )

    _, edges = _project(graph_daos).build()

    edge = next(
        edge for edge in edges
        if edge.relationship_id == relationship_id
    )

    assert edge.relationship_kind == "inferred"
    assert edge.confidence == 0.7


def test_inactive_or_revoked_entities_are_not_projected(graph_daos):
    collective, entities, mentions, resolutions, relationships = graph_daos

    entry_id = _promote(collective, "athena", "mem-1")

    active = entities.create("Active", "project")
    inactive = entities.create("Inactive", "project")
    revoked = entities.create("Revoked", "project")

    entities.update(inactive, status="inactive")
    entities.update(revoked, status="revoked")

    mention_id = mentions.add(
        collective_entry_id=entry_id,
        source_memory_id="mem-1",
        source_profile="athena",
        mention_text="Inactive",
        entity_type="project",
        extraction_method="deterministic-v1",
        confidence=0.8,
    )
    resolutions.create(
        mention_id=mention_id,
        decision="same_entity",
        proposed_entity_id=inactive,
        confidence=1.0,
        resolution_method="normalized-name-v1",
    )

    relationship_id = relationships.create(
        active,
        "related_to",
        revoked,
        confidence=0.8,
        relationship_kind="explicit",
    )

    nodes, edges = _project(graph_daos).build()

    assert all(
        node.entity_id not in {inactive, revoked}
        for node in nodes
    )
    assert all(
        edge.relationship_id != relationship_id
        for edge in edges
    )


def test_projection_is_deterministic(graph_daos):
    collective, entities, mentions, resolutions, relationships = graph_daos

    entry_id = _promote(collective, "athena", "mem-1")
    subject = entities.create("Hermes", "project")
    object_id = entities.create("Mnemosyne", "project")

    mention_id = mentions.add(
        collective_entry_id=entry_id,
        source_memory_id="mem-1",
        source_profile="athena",
        mention_text="Hermes",
        entity_type="project",
        extraction_method="deterministic-v1",
        confidence=0.9,
    )
    resolutions.create(
        mention_id=mention_id,
        decision="same_entity",
        proposed_entity_id=subject,
        confidence=1.0,
        resolution_method="normalized-name-v1",
    )

    relationships.create(
        subject,
        "uses",
        object_id,
        confidence=0.95,
        relationship_kind="explicit",
    )

    projector = _project(graph_daos)

    first = projector.as_dict()
    second = projector.as_dict()

    assert first == second


def test_projection_contains_no_memory_content(graph_daos):
    collective, entities, mentions, resolutions, _ = graph_daos

    entry_id = _promote(collective, "athena", "secret-memory-id")
    entity_id = entities.create("Python", "technology")

    mention_id = mentions.add(
        collective_entry_id=entry_id,
        source_memory_id="secret-memory-id",
        source_profile="athena",
        mention_text="Python",
        entity_type="technology",
        extraction_method="deterministic-v1",
        confidence=0.95,
    )

    resolutions.create(
        mention_id=mention_id,
        decision="same_entity",
        proposed_entity_id=entity_id,
        confidence=1.0,
        resolution_method="normalized-name-v1",
    )

    projection = _project(graph_daos).as_dict()

    serialized = repr(projection)

    assert "secret-memory-content" not in serialized
    assert "memory:collective:" in serialized
    assert "secret-memory-id" in serialized

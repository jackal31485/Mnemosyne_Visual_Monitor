from __future__ import annotations

import sqlite3

import pytest

from src.domain.relationships import RelationshipDAO


def test_schema_is_idempotent(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()
    dao.ensure_schema()

    tables = {
        row[0]
        for row in dao.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    assert "relationships" in tables
    dao.close()


def test_create_and_get_relationship(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    relationship_id = dao.create(
        "entity-a",
        "uses",
        "entity-b",
        confidence=0.95,
    )

    relationship = dao.get(relationship_id)

    assert relationship is not None
    assert relationship["subject_entity_id"] == "entity-a"
    assert relationship["predicate"] == "uses"
    assert relationship["object_entity_id"] == "entity-b"
    assert relationship["confidence"] == 0.95
    assert relationship["status"] == "active"
    assert relationship["relationship_kind"] == "explicit"

    dao.close()


def test_metadata_round_trip(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    relationship_id = dao.create(
        "entity-a",
        "depends_on",
        "entity-b",
        metadata={"source": "deterministic-v1", "version": 1},
    )

    relationship = dao.get(relationship_id)

    assert relationship["metadata_json"] == {
        "source": "deterministic-v1",
        "version": 1,
    }

    dao.close()


@pytest.mark.parametrize(
    "status",
    ["active", "inactive", "revoked", "superseded"],
)
def test_valid_statuses(tmp_path, status):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    relationship_id = dao.create(
        "entity-a",
        "related_to",
        "entity-b",
        status=status,
    )

    assert dao.get(relationship_id)["status"] == status
    dao.close()


@pytest.mark.parametrize("kind", ["explicit", "inferred"])
def test_valid_relationship_kinds(tmp_path, kind):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    relationship_id = dao.create(
        "entity-a",
        "related_to",
        "entity-b",
        relationship_kind=kind,
    )

    assert dao.get(relationship_id)["relationship_kind"] == kind
    dao.close()


def test_explicit_and_inferred_relationships_are_distinct(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    explicit_id = dao.create(
        "entity-a",
        "uses",
        "entity-b",
        relationship_kind="explicit",
    )
    inferred_id = dao.create(
        "entity-a",
        "uses",
        "entity-b",
        relationship_kind="inferred",
    )

    assert explicit_id != inferred_id
    assert len(dao.list()) == 2

    dao.close()


def test_duplicate_relationship_is_rejected(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.create("entity-a", "uses", "entity-b")

    with pytest.raises(sqlite3.IntegrityError):
        dao.create("entity-a", "uses", "entity-b")

    dao.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"subject_entity_id": "", "predicate": "uses", "object_entity_id": "b"},
        {"subject_entity_id": "a", "predicate": "", "object_entity_id": "b"},
        {"subject_entity_id": "a", "predicate": "uses", "object_entity_id": ""},
    ],
)
def test_required_relationship_fields_are_validated(tmp_path, kwargs):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create(**kwargs)

    dao.close()


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_is_bounded(tmp_path, confidence):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create(
            "entity-a",
            "uses",
            "entity-b",
            confidence=confidence,
        )

    dao.close()


def test_invalid_status_is_rejected(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create(
            "entity-a",
            "uses",
            "entity-b",
            status="merged",
        )

    dao.close()


def test_invalid_relationship_kind_is_rejected(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create(
            "entity-a",
            "uses",
            "entity-b",
            relationship_kind="guess",
        )

    dao.close()


def test_update_changes_governed_metadata(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    relationship_id = dao.create(
        "entity-a",
        "uses",
        "entity-b",
        confidence=0.5,
    )

    assert dao.update(
        relationship_id,
        confidence=0.9,
        status="superseded",
        relationship_kind="inferred",
        metadata={"reason": "model-upgrade"},
    )

    relationship = dao.get(relationship_id)

    assert relationship["confidence"] == 0.9
    assert relationship["status"] == "superseded"
    assert relationship["relationship_kind"] == "inferred"
    assert relationship["metadata_json"] == {"reason": "model-upgrade"}

    dao.close()


def test_update_missing_relationship_returns_false(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    assert dao.update("missing", status="revoked") is False

    dao.close()


def test_deterministic_filtered_listing(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.create("z", "uses", "b", relationship_id="r-2")
    dao.create("a", "uses", "b", relationship_id="r-1")
    dao.create("a", "contains", "c", relationship_id="r-3")

    relationships = dao.list(subject_entity_id="a", predicate="uses")

    assert [item["relationship_id"] for item in relationships] == ["r-1"]

    dao.close()


def test_qualified_entity_identity_is_preserved(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    relationship_id = dao.create(
        "agent-a:athena",
        "related_to",
        "Athena",
    )

    relationship = dao.get(relationship_id)

    assert relationship["subject_entity_id"] == "agent-a:athena"
    assert relationship["object_entity_id"] == "Athena"

    dao.close()


def test_relationship_table_contains_no_memory_content_columns(tmp_path):
    dao = RelationshipDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    columns = {
        row["name"]
        for row in dao.conn.execute("PRAGMA table_info('relationships')")
    }

    assert "memory_content" not in columns
    assert "content" not in columns
    assert "source_memory_content" not in columns
    assert "origin_memory_id" not in columns

    dao.close()

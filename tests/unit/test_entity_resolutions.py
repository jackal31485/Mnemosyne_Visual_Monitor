import sqlite3

import pytest

from src.domain.entity_resolutions import EntityResolutionDAO


def test_resolution_schema_is_created_and_idempotent(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")

    dao.ensure_schema()
    dao.ensure_schema()

    tables = {
        row["name"]
        for row in dao.conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    assert "entity_resolutions" in tables


def test_create_and_get_resolution(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    resolution_id = dao.create(
        mention_id="mention-1",
        proposed_entity_id="entity-1",
        decision="same_entity",
        confidence=0.93,
        resolution_method="rules-v1",
        evidence={"reason": "normalized_name"},
        metadata={"reviewed": False},
    )

    resolution = dao.get(resolution_id)

    assert resolution is not None
    assert resolution["resolution_id"] == resolution_id
    assert resolution["mention_id"] == "mention-1"
    assert resolution["proposed_entity_id"] == "entity-1"
    assert resolution["decision"] == "same_entity"
    assert resolution["confidence"] == pytest.approx(0.93)
    assert resolution["resolution_method"] == "rules-v1"
    assert resolution["evidence"] == {"reason": "normalized_name"}
    assert resolution["metadata"] == {"reviewed": False}


def test_resolution_can_remain_ambiguous_without_entity(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    resolution_id = dao.create(
        mention_id="mention-1",
        decision="ambiguous",
        confidence=0.42,
        resolution_method="rules-v1",
        evidence={"candidates": ["entity-a", "entity-b"]},
    )

    resolution = dao.get(resolution_id)

    assert resolution["decision"] == "ambiguous"
    assert resolution["proposed_entity_id"] is None


def test_new_entity_decision_does_not_require_entity_id(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    resolution_id = dao.create(
        mention_id="mention-1",
        decision="new_entity",
        confidence=0.88,
        resolution_method="rules-v1",
    )

    resolution = dao.get(resolution_id)

    assert resolution["decision"] == "new_entity"
    assert resolution["proposed_entity_id"] is None


def test_unresolved_and_rejected_are_valid(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    unresolved = dao.create(
        mention_id="mention-1",
        decision="unresolved",
        resolution_method="pending",
    )

    rejected = dao.create(
        mention_id="mention-2",
        decision="rejected",
        resolution_method="governance-v1",
    )

    assert dao.get(unresolved)["decision"] == "unresolved"
    assert dao.get(rejected)["decision"] == "rejected"


def test_duplicate_mention_resolution_is_rejected(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.create(
        mention_id="mention-1",
        decision="ambiguous",
        resolution_method="rules-v1",
    )

    with pytest.raises(sqlite3.IntegrityError):
        dao.create(
            mention_id="mention-1",
            decision="same_entity",
            proposed_entity_id="entity-1",
            resolution_method="rules-v1",
        )


def test_confidence_is_bounded(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create(
            mention_id="mention-1",
            decision="ambiguous",
            confidence=1.1,
            resolution_method="rules-v1",
        )

    with pytest.raises(ValueError):
        dao.create(
            mention_id="mention-2",
            decision="ambiguous",
            confidence=-0.1,
            resolution_method="rules-v1",
        )


def test_invalid_decision_is_rejected(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create(
            mention_id="mention-1",
            decision="merged",
            resolution_method="rules-v1",
        )


def test_lookup_by_mention(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    resolution_id = dao.create(
        mention_id="mention-1",
        decision="same_entity",
        proposed_entity_id="entity-1",
        resolution_method="rules-v1",
    )

    result = dao.get_for_mention("mention-1")

    assert result["resolution_id"] == resolution_id


def test_list_filters_deterministically(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    first = dao.create(
        mention_id="mention-a",
        decision="ambiguous",
        resolution_method="rules-v1",
    )
    second = dao.create(
        mention_id="mention-b",
        decision="same_entity",
        proposed_entity_id="entity-1",
        resolution_method="rules-v1",
    )

    assert [
        item["resolution_id"]
        for item in dao.list(decision="same_entity")
    ] == [second]

    assert [
        item["resolution_id"]
        for item in dao.list(proposed_entity_id="entity-1")
    ] == [second]

    assert {
        item["resolution_id"]
        for item in dao.list()
    } == {first, second}


def test_resolution_has_no_memory_content_columns(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    columns = {
        row["name"]
        for row in dao.conn.execute(
            "PRAGMA table_info('entity_resolutions')"
        )
    }

    assert "content" not in columns
    assert "memory_content" not in columns
    assert "source_memory_content" not in columns


def test_qualified_entity_identity_is_stored_without_flattening(tmp_path):
    dao = EntityResolutionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    resolution_id = dao.create(
        mention_id="mention-athena",
        proposed_entity_id="agent-a:athena",
        decision="same_entity",
        resolution_method="identity-v1",
    )

    resolution = dao.get(resolution_id)

    assert resolution["proposed_entity_id"] == "agent-a:athena"


def test_existing_collective_entries_are_untouched(tmp_path):
    db = tmp_path / "collective.db"

    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE collective_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_profile TEXT NOT NULL,
                origin_memory_id TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO collective_entries
                (source_profile, origin_memory_id)
            VALUES (?, ?)
            """,
            ("horus", "memory-1"),
        )
        conn.commit()

    dao = EntityResolutionDAO(db)
    dao.ensure_schema()

    row = dao.conn.execute(
        "SELECT source_profile, origin_memory_id "
        "FROM collective_entries WHERE id = 1"
    ).fetchone()

    assert tuple(row) == ("horus", "memory-1")

import sqlite3

import pytest

from src.domain.entities import EntityDAO


def test_entity_schema_is_created_and_idempotent(tmp_path):
    db = tmp_path / "collective.db"
    dao = EntityDAO(db)

    dao.ensure_schema()
    dao.ensure_schema()

    tables = {
        row["name"]
        for row in dao.conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    assert "entities" in tables


def test_create_and_get_entity(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    entity_id = dao.create(
        "Hermes",
        "project",
        confidence=0.95,
        metadata={"source": "phase10"},
    )

    entity = dao.get(entity_id)

    assert entity is not None
    assert entity["entity_id"] == entity_id
    assert entity["canonical_name"] == "Hermes"
    assert entity["entity_type"] == "project"
    assert entity["status"] == "active"
    assert entity["confidence"] == pytest.approx(0.95)
    assert entity["metadata"] == {"source": "phase10"}


def test_entity_has_no_memory_content_column(tmp_path):
    db = tmp_path / "collective.db"
    dao = EntityDAO(db)
    dao.ensure_schema()

    columns = {
        row["name"]
        for row in dao.conn.execute("PRAGMA table_info('entities')")
    }

    assert "memory_content" not in columns
    assert "content" not in columns
    assert "origin_memory_id" not in columns


def test_confidence_is_bounded(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create("Hermes", "project", confidence=1.1)

    with pytest.raises(ValueError):
        dao.create("Hermes", "project", confidence=-0.1)


def test_empty_identity_fields_are_rejected(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.create("", "project")

    with pytest.raises(ValueError):
        dao.create("Hermes", "")


def test_update_preserves_identity(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    entity_id = dao.create("Hermes", "project")

    assert dao.update(
        entity_id,
        canonical_name="Hermes Project",
        confidence=0.8,
    )

    entity = dao.get(entity_id)

    assert entity["entity_id"] == entity_id
    assert entity["canonical_name"] == "Hermes Project"
    assert entity["confidence"] == pytest.approx(0.8)


def test_update_missing_entity_returns_false(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    assert dao.update("does-not-exist", canonical_name="X") is False


def test_invalid_status_is_rejected(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    entity_id = dao.create("Hermes", "project")

    with pytest.raises(ValueError):
        dao.update(entity_id, status="deleted")


def test_list_is_deterministic(tmp_path):
    dao = EntityDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    first = dao.create("Zeta", "concept")
    second = dao.create("Alpha", "concept")

    entities = dao.list()

    assert [entity["entity_id"] for entity in entities] == sorted(
        [first, second]
    )


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

    dao = EntityDAO(db)
    dao.ensure_schema()

    row = dao.conn.execute(
        "SELECT source_profile, origin_memory_id "
        "FROM collective_entries WHERE id = 1"
    ).fetchone()

    assert tuple(row) == ("horus", "memory-1")

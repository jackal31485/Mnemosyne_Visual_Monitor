import sqlite3

import pytest

from src.domain.entity_evidence import EntityEvidenceDAO


def test_evidence_schema_is_created_and_idempotent(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")

    dao.ensure_schema()
    dao.ensure_schema()

    tables = {
        row["name"]
        for row in dao.conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }

    assert "entity_evidence" in tables


def test_add_and_get_evidence(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    evidence_id = dao.add(
        entity_id="entity-1",
        collective_entry_id=42,
        source_memory_id="memory-7",
        source_profile="athena",
        original_mention="Mnemosyne",
        extraction_method="deterministic",
        confidence=0.93,
    )

    evidence = dao.get(evidence_id)

    assert evidence is not None
    assert evidence["evidence_id"] == evidence_id
    assert evidence["entity_id"] == "entity-1"
    assert evidence["collective_entry_id"] == 42
    assert evidence["source_memory_id"] == "memory-7"
    assert evidence["source_profile"] == "athena"
    assert evidence["original_mention"] == "Mnemosyne"
    assert evidence["extraction_method"] == "deterministic"
    assert evidence["confidence"] == pytest.approx(0.93)


def test_evidence_contains_no_memory_content_column(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    columns = {
        row["name"]
        for row in dao.conn.execute(
            "PRAGMA table_info('entity_evidence')"
        )
    }

    assert "content" not in columns
    assert "memory_content" not in columns


def test_confidence_is_bounded(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.add(
            entity_id="entity-1",
            collective_entry_id=1,
            source_memory_id="memory-1",
            source_profile="athena",
            original_mention="Hermes",
            extraction_method="test",
            confidence=1.1,
        )

    with pytest.raises(ValueError):
        dao.add(
            entity_id="entity-2",
            collective_entry_id=2,
            source_memory_id="memory-2",
            source_profile="athena",
            original_mention="Hermes",
            extraction_method="test",
            confidence=-0.1,
        )


def test_required_provenance_fields_are_validated(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    fields = [
        ("entity_id", ""),
        ("source_memory_id", ""),
        ("source_profile", ""),
        ("original_mention", ""),
        ("extraction_method", ""),
    ]

    for field, value in fields:
        kwargs = {
            "entity_id": "entity-1",
            "collective_entry_id": 1,
            "source_memory_id": "memory-1",
            "source_profile": "athena",
            "original_mention": "Hermes",
            "extraction_method": "test",
        }
        kwargs[field] = value

        with pytest.raises(ValueError):
            dao.add(**kwargs)


def test_collective_entry_id_must_be_positive_integer(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    for value in (0, -1, True, "1"):
        with pytest.raises(ValueError):
            dao.add(
                entity_id="entity-1",
                collective_entry_id=value,
                source_memory_id="memory-1",
                source_profile="athena",
                original_mention="Hermes",
                extraction_method="test",
            )


def test_duplicate_evidence_is_rejected(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    kwargs = {
        "entity_id": "entity-1",
        "collective_entry_id": 1,
        "source_memory_id": "memory-1",
        "source_profile": "athena",
        "original_mention": "Hermes",
        "extraction_method": "deterministic",
    }

    dao.add(**kwargs)

    with pytest.raises(sqlite3.IntegrityError):
        dao.add(**kwargs)


def test_list_is_deterministic_and_filterable(tmp_path):
    dao = EntityEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.add(
        entity_id="entity-b",
        collective_entry_id=2,
        source_memory_id="memory-2",
        source_profile="odin",
        original_mention="Hermes",
        extraction_method="test",
    )
    dao.add(
        entity_id="entity-a",
        collective_entry_id=1,
        source_memory_id="memory-1",
        source_profile="athena",
        original_mention="Mnemosyne",
        extraction_method="test",
    )

    all_evidence = dao.list()
    assert [item["entity_id"] for item in all_evidence] == [
        "entity-a",
        "entity-b",
    ]

    assert len(dao.list(entity_id="entity-a")) == 1
    assert len(dao.list(collective_entry_id=2)) == 1
    assert len(dao.list(source_profile="athena")) == 1


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

    dao = EntityEvidenceDAO(db)
    dao.ensure_schema()

    row = dao.conn.execute(
        "SELECT source_profile, origin_memory_id "
        "FROM collective_entries WHERE id = 1"
    ).fetchone()

    assert tuple(row) == ("horus", "memory-1")

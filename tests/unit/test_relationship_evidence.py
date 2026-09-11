from __future__ import annotations

import sqlite3

import pytest

from src.domain.relationship_evidence import RelationshipEvidenceDAO


def test_schema_is_idempotent(tmp_path):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()
    dao.ensure_schema()

    tables = {
        row[0]
        for row in dao.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    assert "relationship_evidence" in tables
    dao.close()


def test_add_and_get_evidence(tmp_path):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    evidence_id = dao.add(
        relationship_id="relationship-a",
        collective_entry_id=7,
        source_memory_id="memory-7",
        source_profile="agent-a:athena",
        evidence_reference="collective-entry:7",
        extraction_method="deterministic-v1",
        confidence=0.91,
    )

    evidence = dao.get(evidence_id)

    assert evidence is not None
    assert evidence["relationship_id"] == "relationship-a"
    assert evidence["collective_entry_id"] == 7
    assert evidence["source_memory_id"] == "memory-7"
    assert evidence["source_profile"] == "agent-a:athena"
    assert evidence["evidence_reference"] == "collective-entry:7"
    assert evidence["extraction_method"] == "deterministic-v1"
    assert evidence["confidence"] == 0.91

    dao.close()


def test_duplicate_evidence_is_rejected(tmp_path):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    kwargs = {
        "relationship_id": "relationship-a",
        "collective_entry_id": 7,
        "source_memory_id": "memory-7",
        "source_profile": "athena",
        "evidence_reference": "collective-entry:7",
        "extraction_method": "deterministic-v1",
    }

    dao.add(**kwargs)

    with pytest.raises(sqlite3.IntegrityError):
        dao.add(**kwargs)

    dao.close()


@pytest.mark.parametrize(
    "field, value",
    [
        ("relationship_id", ""),
        ("source_memory_id", ""),
        ("source_profile", ""),
        ("evidence_reference", ""),
        ("extraction_method", ""),
    ],
)
def test_required_text_fields_are_validated(tmp_path, field, value):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    kwargs = {
        "relationship_id": "relationship-a",
        "collective_entry_id": 7,
        "source_memory_id": "memory-7",
        "source_profile": "athena",
        "evidence_reference": "collective-entry:7",
        "extraction_method": "deterministic-v1",
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        dao.add(**kwargs)

    dao.close()


@pytest.mark.parametrize(
    "value",
    [0, -1, True, False],
)
def test_collective_entry_id_must_be_positive_integer(tmp_path, value):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.add(
            relationship_id="relationship-a",
            collective_entry_id=value,
            source_memory_id="memory-7",
            source_profile="athena",
            evidence_reference="collective-entry:7",
            extraction_method="deterministic-v1",
        )

    dao.close()


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_is_bounded(tmp_path, confidence):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError):
        dao.add(
            relationship_id="relationship-a",
            collective_entry_id=7,
            source_memory_id="memory-7",
            source_profile="athena",
            evidence_reference="collective-entry:7",
            extraction_method="deterministic-v1",
            confidence=confidence,
        )

    dao.close()


def test_deterministic_filtered_listing(tmp_path):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.add(
        relationship_id="relationship-b",
        collective_entry_id=8,
        source_memory_id="memory-8",
        source_profile="odin",
        evidence_reference="collective-entry:8",
        extraction_method="method",
        evidence_id="evidence-2",
    )
    dao.add(
        relationship_id="relationship-a",
        collective_entry_id=7,
        source_memory_id="memory-7",
        source_profile="athena",
        evidence_reference="collective-entry:7",
        extraction_method="method",
        evidence_id="evidence-1",
    )

    evidence = dao.list(source_profile="athena")

    assert [item["evidence_id"] for item in evidence] == ["evidence-1"]

    dao.close()


def test_qualified_source_profile_is_preserved(tmp_path):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    evidence_id = dao.add(
        relationship_id="relationship-a",
        collective_entry_id=7,
        source_memory_id="memory-7",
        source_profile="agent-id:athena",
        evidence_reference="collective-entry:7",
        extraction_method="method",
    )

    assert dao.get(evidence_id)["source_profile"] == "agent-id:athena"

    dao.close()


def test_no_memory_content_columns(tmp_path):
    dao = RelationshipEvidenceDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    columns = {
        row["name"]
        for row in dao.conn.execute(
            "PRAGMA table_info('relationship_evidence')"
        )
    }

    assert "memory_content" not in columns
    assert "content" not in columns
    assert "source_memory_content" not in columns
    assert "evidence_text" not in columns

    dao.close()


def test_existing_collective_entries_are_untouched(tmp_path):
    db_path = tmp_path / "collective.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE collective_entries (
            id INTEGER PRIMARY KEY,
            source_profile TEXT,
            origin_memory_id TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO collective_entries
        (id, source_profile, origin_memory_id)
        VALUES (1, 'athena', 'memory-1')
        """
    )
    conn.commit()
    conn.close()

    dao = RelationshipEvidenceDAO(db_path)
    dao.ensure_schema()

    row = dao.conn.execute(
        "SELECT * FROM collective_entries WHERE id = 1"
    ).fetchone()

    assert row["source_profile"] == "athena"
    assert row["origin_memory_id"] == "memory-1"

    dao.close()

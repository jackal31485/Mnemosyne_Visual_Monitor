from __future__ import annotations

import sqlite3

import pytest

from src.domain.entity_mentions import EntityMentionDAO


def test_schema_is_idempotent(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")

    dao.ensure_schema()
    dao.ensure_schema()

    row = dao.conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'entity_mentions'
        """
    ).fetchone()

    assert row["name"] == "entity_mentions"
    dao.close()


def test_add_and_get_preserves_provenance(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    mention_id = dao.add(
        collective_entry_id=12,
        source_memory_id="memory-42",
        source_profile="agent-a:horus",
        mention_text="Mnemosyne",
        entity_type="technology",
        confidence=0.95,
        extraction_method="deterministic-v1",
        mention_id="mention-1",
    )

    assert mention_id == "mention-1"

    result = dao.get("mention-1")

    assert result == {
        "mention_id": "mention-1",
        "collective_entry_id": 12,
        "source_memory_id": "memory-42",
        "source_profile": "agent-a:horus",
        "mention_text": "Mnemosyne",
        "entity_type": "technology",
        "confidence": 0.95,
        "extraction_method": "deterministic-v1",
        "extracted_at": result["extracted_at"],
    }

    dao.close()


def test_schema_contains_no_memory_content_column(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    columns = {
        row["name"]
        for row in dao.conn.execute(
            "PRAGMA table_info(entity_mentions)"
        ).fetchall()
    }

    assert "content" not in columns
    assert "memory_content" not in columns

    dao.close()


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_is_bounded(tmp_path, confidence):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    with pytest.raises(ValueError, match="confidence"):
        dao.add(
            collective_entry_id=1,
            source_memory_id="memory-1",
            source_profile="athena",
            mention_text="Mnemosyne",
            entity_type="technology",
            extraction_method="deterministic-v1",
            confidence=confidence,
        )

    dao.close()


def test_required_provenance_is_validated(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    fields = (
        "source_memory_id",
        "source_profile",
        "mention_text",
        "entity_type",
        "extraction_method",
    )

    for field in fields:
        values = {
            "source_memory_id": "memory-1",
            "source_profile": "athena",
            "mention_text": "Mnemosyne",
            "entity_type": "technology",
            "extraction_method": "deterministic-v1",
        }
        values[field] = ""

        with pytest.raises(ValueError, match=field):
            dao.add(
                collective_entry_id=1,
                **values,
            )

    dao.close()


def test_collective_entry_id_must_be_positive_integer(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    for value in (0, -1, True, "1"):
        with pytest.raises(ValueError, match="collective_entry_id"):
            dao.add(
                collective_entry_id=value,
                source_memory_id="memory-1",
                source_profile="athena",
                mention_text="Mnemosyne",
                entity_type="technology",
                extraction_method="deterministic-v1",
            )

    dao.close()


def test_duplicate_mention_is_rejected(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    values = {
        "collective_entry_id": 1,
        "source_memory_id": "memory-1",
        "source_profile": "athena",
        "mention_text": "Mnemosyne",
        "entity_type": "technology",
        "extraction_method": "deterministic-v1",
    }

    dao.add(**values)

    with pytest.raises(sqlite3.IntegrityError):
        dao.add(**values)

    dao.close()


def test_list_is_deterministic_and_filterable(tmp_path):
    dao = EntityMentionDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.add(
        collective_entry_id=2,
        source_memory_id="memory-b",
        source_profile="athena",
        mention_text="SQLite",
        entity_type="technology",
        extraction_method="deterministic-v1",
    )
    dao.add(
        collective_entry_id=1,
        source_memory_id="memory-a",
        source_profile="agent-a:horus",
        mention_text="Mnemosyne",
        entity_type="project",
        extraction_method="deterministic-v1",
    )

    rows = dao.list()
    assert [row["collective_entry_id"] for row in rows] == [1, 2]

    assert len(
        dao.list(source_profile="agent-a:horus")
    ) == 1

    assert len(
        dao.list(entity_type="technology")
    ) == 1

    dao.close()

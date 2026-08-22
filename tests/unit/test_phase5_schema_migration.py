import sqlite3

from src.domain.collective import CollectiveDAO


def table_columns(dao):
    rows = dao.conn.execute(
        "PRAGMA table_info('collective_entries')"
    ).fetchall()
    return {row["name"]: row for row in rows}


def test_fresh_database_has_nullable_embedding_blob(tmp_path):
    db_path = tmp_path / "fresh.db"

    dao = CollectiveDAO(db_path)
    dao.ensure_schema()

    columns = table_columns(dao)

    assert "embedding" in columns
    assert columns["embedding"]["type"].upper() == "BLOB"
    assert columns["embedding"]["notnull"] == 0

    dao.close()


def test_legacy_database_is_migrated(tmp_path):
    db_path = tmp_path / "legacy.db"

    # Create a database using the pre-Phase-5 schema.
    legacy_schema = """
    CREATE TABLE collective_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_profile TEXT NOT NULL,
        origin_memory_id TEXT NOT NULL,
        proposed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        validated_at TEXT,
        validator_profile TEXT,
        validation_score REAL,
        is_revoked BOOLEAN NOT NULL DEFAULT 0,
        revocation_reason TEXT,
        is_promoted BOOLEAN NOT NULL DEFAULT 0
    );
    """

    conn = sqlite3.connect(db_path)
    conn.execute(legacy_schema)
    conn.execute(
        """
        INSERT INTO collective_entries
            (source_profile, origin_memory_id, validation_score)
        VALUES (?, ?, ?)
        """,
        ("athena", "memory-legacy", 0.91),
    )
    conn.commit()
    conn.close()

    dao = CollectiveDAO(db_path)
    dao.ensure_schema()

    columns = table_columns(dao)

    assert "embedding" in columns
    assert columns["embedding"]["type"].upper() == "BLOB"

    row = dao.conn.execute(
        """
        SELECT source_profile, origin_memory_id, validation_score, embedding
        FROM collective_entries
        WHERE id = 1
        """
    ).fetchone()

    assert row["source_profile"] == "athena"
    assert row["origin_memory_id"] == "memory-legacy"
    assert row["validation_score"] == 0.91
    assert row["embedding"] is None

    dao.close()


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "idempotent.db"

    dao = CollectiveDAO(db_path)

    dao.ensure_schema()
    dao.ensure_schema()
    dao.ensure_schema()

    columns = table_columns(dao)

    assert "embedding" in columns
    assert columns["embedding"]["type"].upper() == "BLOB"

    embedding_columns = [
        name for name in columns if name == "embedding"
    ]

    assert embedding_columns == ["embedding"]

    dao.close()


def test_existing_records_survive_migration(tmp_path):
    db_path = tmp_path / "existing.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE collective_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_profile TEXT NOT NULL,
            origin_memory_id TEXT NOT NULL,
            proposed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            validated_at TEXT,
            validator_profile TEXT,
            validation_score REAL,
            is_revoked BOOLEAN NOT NULL DEFAULT 0,
            revocation_reason TEXT,
            is_promoted BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )

    conn.execute(
        """
        INSERT INTO collective_entries
            (source_profile, origin_memory_id, validation_score,
             is_revoked, revocation_reason, is_promoted)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("hawk", "memory-42", 0.88, 1, "test revocation", 1),
    )
    conn.commit()
    conn.close()

    dao = CollectiveDAO(db_path)
    dao.ensure_schema()

    row = dao.conn.execute(
        """
        SELECT *
        FROM collective_entries
        WHERE origin_memory_id = ?
        """,
        ("memory-42",),
    ).fetchone()

    assert row is not None
    assert row["source_profile"] == "hawk"
    assert row["origin_memory_id"] == "memory-42"
    assert row["validation_score"] == 0.88
    assert row["is_revoked"] == 1
    assert row["revocation_reason"] == "test revocation"
    assert row["is_promoted"] == 1
    assert row["embedding"] is None

    dao.close()


def test_new_entries_can_omit_embedding(tmp_path):
    db_path = tmp_path / "new_entry.db"

    dao = CollectiveDAO(db_path)
    dao.ensure_schema()

    entry_id = dao.add_entry("pope", "memory-new")

    row = dao.conn.execute(
        """
        SELECT origin_memory_id, embedding
        FROM collective_entries
        WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()

    assert row["origin_memory_id"] == "memory-new"
    assert row["embedding"] is None

    dao.close()

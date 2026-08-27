import sqlite3
from pathlib import Path

import pytest

import src.domain.collective as collective
import src.domain.profile_ingest as profile_ingest
from src.domain.profile_ingest import (
    discover_profile_paths,
    extract_memories,
    infer_memory_table,
    ingest_profiles,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_profile(root: Path, name: str, rows, table_name: str = "working_memory"):
    """Create a minimal Hermes profile containing a Mnemosyne SQLite database."""
    profile_dir = root / name
    db_path = profile_dir / "mnemosyne" / "data" / "mnemosyne.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            f"""
            CREATE TABLE {table_name} (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL
            )
            """
        )

        for row in rows:
            conn.execute(
                f"INSERT INTO {table_name} (id, content) VALUES (?, ?)",
                (row["id"], row.get("content", "")),
            )

        conn.commit()
    finally:
        conn.close()

    return profile_dir, db_path


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path: Path):
    """
    Isolate every ingestion test from the user's real Hermes profiles and
    project collective database.
    """

    # Redirect the collective database used by CollectiveDAO().
    tmp_db = tmp_path / "collective.db"
    monkeypatch.setattr(collective, "DB_PATH", tmp_db)

    # ingest_profiles() resolves discover_profile_paths from the
    # profile_ingest module at call time. Replace that reference with a
    # temporary-directory-only discovery function.
    def fake_discover(base=None):
        profiles = []

        for path in sorted(tmp_path.iterdir()):
            if not path.is_dir():
                continue

            db_path = path / "mnemosyne" / "data" / "mnemosyne.db"
            if db_path.is_file():
                profiles.append(path)

        return profiles

    monkeypatch.setattr(
        profile_ingest,
        "discover_profile_paths",
        fake_discover,
    )

    # Ensure the isolated collective schema exists before each test.
    dao = collective.CollectiveDAO(tmp_db)
    dao.ensure_schema()
    dao.close()


def collective_rows():
    """Return all collective entries from the isolated test database."""
    dao = collective.CollectiveDAO()
    try:
        return dao.conn.execute(
            "SELECT * FROM collective_entries ORDER BY id"
        ).fetchall()
    finally:
        dao.close()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def test_profile_discovery(tmp_path: Path):
    athena, _ = make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": "first"}],
    )

    (tmp_path / "lonely").mkdir()

    assert discover_profile_paths(tmp_path) == [athena]


# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------

def test_infer_memory_table(tmp_path: Path):
    _, db_path = make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": "first"}],
    )

    conn = sqlite3.connect(str(db_path))
    try:
        assert infer_memory_table(conn) == "working_memory"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Memory extraction
# ---------------------------------------------------------------------------

def test_memory_extraction(tmp_path: Path):
    _, db_path = make_profile(
        tmp_path,
        "athena",
        [
            {"id": "m1", "content": "first"},
            {"id": "m2", "content": "second"},
        ],
    )

    rows = list(extract_memories(db_path))

    assert len(rows) == 2
    assert {row["id"] for row in rows} == {"m1", "m2"}
    assert {row["content"] for row in rows} == {"first", "second"}


# ---------------------------------------------------------------------------
# Dry-run ingestion
# ---------------------------------------------------------------------------

def test_dry_run_ingestion(tmp_path: Path):
    make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": "first"}],
    )

    result = ingest_profiles(dry_run=True)

    assert result == {"athena": 1}
    assert collective_rows() == []


# ---------------------------------------------------------------------------
# Proposal creation
# ---------------------------------------------------------------------------

def test_proposal_creation(tmp_path: Path):
    make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": "first"}],
    )

    result = ingest_profiles(dry_run=False)

    assert result == {"athena": 1}

    rows = collective_rows()

    assert len(rows) == 1
    assert rows[0]["source_profile"] == "athena"
    assert rows[0]["origin_memory_id"] == "m1"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_ingestion_is_idempotent(tmp_path: Path):
    make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": "first"}],
    )

    first = ingest_profiles(dry_run=False)
    second = ingest_profiles(dry_run=False)

    assert first == {"athena": 1}
    assert second == {"athena": 1}

    rows = collective_rows()

    assert len(rows) == 1
    assert rows[0]["source_profile"] == "athena"
    assert rows[0]["origin_memory_id"] == "m1"


# ---------------------------------------------------------------------------
# Privacy boundary
# ---------------------------------------------------------------------------

def test_raw_memory_content_is_not_stored_in_collective(
    tmp_path: Path,
):
    secret = "THIS_RAW_MEMORY_MUST_NOT_APPEAR_IN_COLLECTIVE_DB_12345"

    make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": secret}],
    )

    ingest_profiles(dry_run=False)

    rows = collective_rows()

    assert len(rows) == 1

    for row in rows:
        assert secret not in str(tuple(row))


# ---------------------------------------------------------------------------
# Read-only source database
# ---------------------------------------------------------------------------

def test_source_database_is_unchanged_by_ingestion(
    tmp_path: Path,
):
    _, db_path = make_profile(
        tmp_path,
        "athena",
        [
            {"id": "m1", "content": "first"},
            {"id": "m2", "content": "second"},
        ],
    )

    before_conn = sqlite3.connect(str(db_path))
    try:
        before_rows = before_conn.execute(
            "SELECT * FROM working_memory ORDER BY id"
        ).fetchall()

        before_tables = before_conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()
    finally:
        before_conn.close()

    ingest_profiles(dry_run=False)

    after_conn = sqlite3.connect(str(db_path))
    try:
        after_rows = after_conn.execute(
            "SELECT * FROM working_memory ORDER BY id"
        ).fetchall()

        after_tables = after_conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()
    finally:
        after_conn.close()

    assert after_rows == before_rows
    assert after_tables == before_tables


# ---------------------------------------------------------------------------
# Missing / invalid profile handling
# ---------------------------------------------------------------------------

def test_missing_profile_is_ignored(tmp_path: Path):
    (tmp_path / "empty_profile").mkdir()

    result = ingest_profiles(dry_run=False)

    assert result == {}
    assert collective_rows() == []


# ---------------------------------------------------------------------------
# Multiple profiles and cross-profile isolation
# ---------------------------------------------------------------------------

def test_multiple_profiles_remain_distinct(tmp_path: Path):
    make_profile(
        tmp_path,
        "athena",
        [{"id": "m1", "content": "athena memory"}],
    )

    make_profile(
        tmp_path,
        "thoth",
        [{"id": "m1", "content": "thoth memory"}],
    )

    result = ingest_profiles(dry_run=False)

    assert result == {
        "athena": 1,
        "thoth": 1,
    }

    rows = collective_rows()

    assert len(rows) == 2

    identities = {
        (row["source_profile"], row["origin_memory_id"])
        for row in rows
    }

    assert identities == {
        ("athena", "m1"),
        ("thoth", "m1"),
    }


# ---------------------------------------------------------------------------
# Multiple memories from one profile
# ---------------------------------------------------------------------------

def test_all_memories_are_ingested_as_proposals(tmp_path: Path):
    make_profile(
        tmp_path,
        "athena",
        [
            {"id": "m1", "content": "first"},
            {"id": "m2", "content": "second"},
            {"id": "m3", "content": "third"},
        ],
    )

    result = ingest_profiles(dry_run=False)

    assert result == {"athena": 3}

    rows = collective_rows()

    assert len(rows) == 3

    identities = {
        (row["source_profile"], row["origin_memory_id"])
        for row in rows
    }

    assert identities == {
        ("athena", "m1"),
        ("athena", "m2"),
        ("athena", "m3"),
    }

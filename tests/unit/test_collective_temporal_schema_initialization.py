import sqlite3

from src.domain.collective import CollectiveDAO


def _tables(db_path):
    with sqlite3.connect(db_path) as conn:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }


def test_collective_initialization_creates_temporal_evidence(tmp_path):
    db_path = tmp_path / "collective.db"

    dao = CollectiveDAO(db_path)
    dao.ensure_schema()

    tables = _tables(db_path)

    assert "collective_entries" in tables
    assert "collective_provenance" in tables
    assert "temporal_evidence" in tables


def test_collective_initialization_is_idempotent(tmp_path):
    db_path = tmp_path / "collective.db"

    dao = CollectiveDAO(db_path)

    dao.ensure_schema()
    first_tables = _tables(db_path)

    dao.ensure_schema()
    second_tables = _tables(db_path)

    assert first_tables == second_tables
    assert "temporal_evidence" in second_tables

#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from typing import Any, Iterable

# Constants for the collective database location.
DB_PATH = Path("data") / "collective.db"
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS collective_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_profile TEXT      NOT NULL,
    origin_memory_id TEXT     NOT NULL,
    proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    validator_profile TEXT,
    validation_score REAL,
    is_revoked BOOLEAN NOT NULL DEFAULT 0,
    revocation_reason TEXT
);
"""

class CollectiveDAO:
    """Repository wrapper around the SQLite collective database.

    The API is deliberately minimal – only what Stage 1 tests require. It allows
    creating the DB, inspecting tables and performing simple CRUD operations on
    the ``collective_entries`` table.
    """

    def __init__(self) -> None:
        self._db_path = DB_PATH.absolute()
        # Ensure parent directories exist; SQLite will create file if missing.
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # Lazy connection placeholder
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self, "_conn") or self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), detect_types=sqlite3.PARSE_DECLTYPES)
            # Return rows as tuples (default).
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if hasattr(self, "_conn") and self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------------
    # Schema helpers
    # ---------------------------------------------------------------------
    def ensure_schema(self) -> None:
        """Create the collective schema if it does not exist.

        The call is idempotent – repeated execution leaves the DB unchanged but
        guarantees the table exists and the ``validation_score`` column is of
        type REAL.
        """
        self.conn.execute(SCHEMA_SQL)
        self.conn.commit()

    def get_table_names(self) -> Iterable[str]:
        cur = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return [row["name"] for row in cur.fetchall()]

    # ---------------------------------------------------------------------
    # CRUD operations required by the tests
    # ---------------------------------------------------------------------
    def add_entry(self, source_profile: str, origin_memory_id: str) -> int:
        """Insert a new collective entry and return its integer primary key.

        Only the columns defined in Stage 1 are set; all others default to NULL or 0.
        """
        cur = self.conn.execute(
            "INSERT INTO collective_entries (source_profile, origin_memory_id) VALUES (?, ?)",
            (source_profile, origin_memory_id),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_by_id(self, entry_id: int):
        cur = self.conn.execute("SELECT * FROM collective_entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        if row is None:
            return None
        # Convert Row to tuple in the order defined by schema for test expectations.
        return tuple(row)

    def update_entry_revoked(self, entry_id: int, reason: str) -> None:
        self.conn.execute(
            "UPDATE collective_entries SET is_revoked = 1, revocation_reason = ? WHERE id = ?",
            (reason, entry_id),
        )
        self.conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM collective_entries WHERE id = ?", (entry_id,))
        self.conn.commit()

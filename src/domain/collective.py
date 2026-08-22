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
    proposed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    validated_at TEXT,
    validator_profile TEXT,
    validation_score REAL,
    is_revoked BOOLEAN NOT NULL DEFAULT 0,
    revocation_reason TEXT,
    is_promoted BOOLEAN NOT NULL DEFAULT 0
);
"""

class CollectiveDAO:
    """Repository wrapper around the SQLite collective database.

    The API is deliberately minimal – only what Stage 1 tests require. It allows
    creating the DB, inspecting tables and performing simple CRUD operations on
    the ``collective_entries`` table.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Create a DAO using the default or explicitly supplied SQLite database."""
        self._db_path = Path(db_path or DB_PATH).absolute()
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
        """Create the collective schema and migrate legacy databases.

        The operation is idempotent. Existing databases receive the nullable
        ``embedding`` BLOB column without altering existing records.
        """
        self.conn.execute(SCHEMA_SQL)

        columns = {
            row["name"]
            for row in self.conn.execute(
                "PRAGMA table_info('collective_entries')"
            ).fetchall()
        }

        if "embedding" not in columns:
            self.conn.execute(
                "ALTER TABLE collective_entries ADD COLUMN embedding BLOB"
            )

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
        # Map SQLite Row order to test‑expected index layout.
        return (
            row["id"],
            row["source_profile"],
            row["origin_memory_id"],
            row["proposed_at"],
            row["validated_at"],
            row["validation_score"],
            row["validator_profile"],
            row["is_revoked"],
            row["revocation_reason"],
        )

    def update_entry_revoked(self, entry_id: int, reason: str) -> None:
        self.conn.execute(
            "UPDATE collective_entries SET is_revoked = 1, revocation_reason = ? WHERE id = ?",
            (reason, entry_id),
        )
        self.conn.commit()

    def update_entry_promoted(self, entry_id: int) -> None:
        self.conn.execute(
            "UPDATE collective_entries SET is_promoted = 1 WHERE id = ?",
            (entry_id,),
        )
        self.conn.commit()

    def list_promoted(self) -> list[int]:
        """Return IDs of collective entries that have been promoted."""
        cur = self.conn.execute(
            "SELECT id FROM collective_entries WHERE is_promoted = 1 ORDER BY id"
        )
        return [row["id"] for row in cur.fetchall()]

    def get_by_source(self, src: str, orig_mem: str):
        """Return the first matching entry using the legacy 9-field tuple."""
        cur = self.conn.execute(
            """
            SELECT *
            FROM collective_entries
            WHERE source_profile = ?
              AND origin_memory_id = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (src, orig_mem),
        )
        row = cur.fetchone()

        if row is None:
            return None

        return (
            row["id"],
            row["source_profile"],
            row["origin_memory_id"],
            row["proposed_at"],
            row["validated_at"],
            row["validation_score"],
            row["validator_profile"],
            row["is_revoked"],
            row["revocation_reason"],
        )

    def list_by_state(self, state: str) -> list[int]:
        """Return entry IDs matching a lifecycle state, sorted by primary key.

        Supported states:
            proposed, validated, rejected, promoted, revoked
        """
        queries = {
            "proposed": """
                SELECT id FROM collective_entries
                WHERE validated_at IS NULL
                  AND is_revoked = 0
                ORDER BY id
            """,
            "validated": """
                SELECT id FROM collective_entries
                WHERE validated_at IS NOT NULL
                  AND is_revoked = 0
                ORDER BY id
            """,
            "rejected": """
                SELECT id FROM collective_entries
                WHERE is_revoked = 1
                  AND validated_at IS NULL
                ORDER BY id
            """,
            "promoted": """
                SELECT id FROM collective_entries
                WHERE is_promoted = 1
                ORDER BY id
            """,
            "revoked": """
                SELECT id FROM collective_entries
                WHERE is_revoked = 1
                ORDER BY id
            """,
        }

        if state not in queries:
            raise ValueError(
                "Unknown lifecycle state: "
                f"{state!r}. Expected one of: "
                "proposed, validated, rejected, promoted, revoked"
            )

        cur = self.conn.execute(queries[state])
        return [row["id"] for row in cur.fetchall()]

    def list_proposed(self) -> list[int]:
        """Return IDs of proposals awaiting validation."""
        return self.list_by_state("proposed")

    def list_validated(self) -> list[int]:
        """Return IDs of validated, non-revoked entries."""
        return self.list_by_state("validated")

    def list_rejected(self) -> list[int]:
        """Return IDs of rejected entries."""
        return self.list_by_state("rejected")

    def list_revoked(self) -> list[int]:
        """Return IDs of all revoked entries."""
        return self.list_by_state("revoked")

    def revoke_entry(self, entry_id: int, reason: str) -> None:
        """Revoke an entry without altering its provenance or validation data."""
        if not reason:
            raise ValueError("rejection reason cannot be empty")

        cur = self.conn.execute(
            "SELECT is_revoked FROM collective_entries WHERE id = ?",
            (entry_id,),
        )
        row = cur.fetchone()

        if row is None:
            raise KeyError(f"Entry {entry_id} not found")

        if row["is_revoked"]:
            raise ValueError("Entry already revoked")

        self.conn.execute(
            """
            UPDATE collective_entries
            SET is_revoked = 1,
                revocation_reason = ?
            WHERE id = ?
            """,
            (reason, entry_id),
        )
        self.conn.commit()

    def get_lifecycle_state(self, entry_id: int):
        """Return lifecycle state for a collective entry."""
        cur = self.conn.execute(
            """
            SELECT validated_at, is_revoked, revocation_reason, is_promoted
            FROM collective_entries
            WHERE id = ?
            """,
            (entry_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        return (
            row["validated_at"],
            row["is_revoked"],
            row["revocation_reason"],
            row["is_promoted"],
        )

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM collective_entries WHERE id = ?", (entry_id,))
        self.conn.commit()


    # ---------------------------------------------------------------------
    # Stage 2 – Reference & provenance metadata support
    # ---------------------------------------------------------------------
    def insert_collective_entry(
        self,
        source_profile: str,
        origin_memory_id: str,
        *,
        proposed_at: str | None = None,
        validator_profile: str | None = None,
        validated_at: str | None = None,
        validation_score: float | None = None
    ) -> int:
        """Insert a new reference with optional provenance.

        The method validates that ``source_profile`` and ``origin_memory_id`` are
        non‑empty strings; raw memory content is never accepted.
        All other parameters are stored verbatim in the corresponding columns.
        """
        if not source_profile:
            raise ValueError("source_profile cannot be empty")
        if not origin_memory_id:
            raise ValueError("origin_memory_id cannot be empty")

        cur = self.conn.execute(
            "INSERT INTO collective_entries (\n                source_profile, origin_memory_id,\n                proposed_at, validator_profile, validated_at, validation_score\n            ) VALUES (?, ?, ?, ?, ?, ?)",
            (
                source_profile,
                origin_memory_id,
                proposed_at,
                validator_profile,
                validated_at,
                validation_score,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

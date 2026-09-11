"""Entity foundation for Mnemosyne's collective knowledge layer.

Phase 10A.1 establishes durable entity identity only.

Entities are derived collective structures.  They do not contain private
memory content.  Evidence, mentions, aliases, relationships, and resolution
decisions are introduced by later Phase 10 milestones.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "collective.db"

ENTITY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    confidence REAL,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entities_canonical_name
    ON entities(canonical_name);

CREATE INDEX IF NOT EXISTS idx_entities_type
    ON entities(entity_type);

CREATE INDEX IF NOT EXISTS idx_entities_status
    ON entities(status);
"""


class EntityDAO:
    """SQLite repository for Phase 10 entity records.

    This DAO deliberately stores identity metadata only.  It does not store
    memory content or make entity-resolution decisions.
    """

    VALID_STATUSES = frozenset({"active", "inactive", "merged", "revoked"})

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path or DB_PATH).absolute()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path),
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def ensure_schema(self) -> None:
        """Create the entity schema idempotently."""
        self.conn.executescript(ENTITY_SCHEMA_SQL)
        self.conn.commit()

    def create(
        self,
        canonical_name: str,
        entity_type: str,
        *,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
        entity_id: str | None = None,
    ) -> str:
        """Create an entity and return its stable identifier."""
        canonical_name = canonical_name.strip()
        entity_type = entity_type.strip()

        if not canonical_name:
            raise ValueError("canonical_name must not be empty")
        if not entity_type:
            raise ValueError("entity_type must not be empty")
        _validate_confidence(confidence)

        entity_id = entity_id or str(uuid.uuid4())
        metadata_json = (
            json.dumps(metadata, sort_keys=True, separators=(",", ":"))
            if metadata is not None
            else None
        )

        self.conn.execute(
            """
            INSERT INTO entities (
                entity_id,
                canonical_name,
                entity_type,
                confidence,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entity_id,
                canonical_name,
                entity_type,
                confidence,
                metadata_json,
            ),
        )
        self.conn.commit()
        return entity_id

    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Return one entity as a plain dictionary."""
        row = self.conn.execute(
            "SELECT * FROM entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_entity(row)

    def list(
        self,
        *,
        entity_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return entities in deterministic entity-ID order."""
        clauses: list[str] = []
        params: list[Any] = []

        if entity_type is not None:
            clauses.append("entity_type = ?")
            params.append(entity_type)

        if status is not None:
            _validate_status(status)
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM entities
            {where}
            ORDER BY entity_id
            """,
            params,
        ).fetchall()

        return [_row_to_entity(row) for row in rows]

    def update(
        self,
        entity_id: str,
        *,
        canonical_name: str | None = None,
        entity_type: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update mutable entity metadata.

        Returns False when the entity does not exist.
        """
        existing = self.get(entity_id)
        if existing is None:
            return False

        if canonical_name is None:
            canonical_name = existing["canonical_name"]
        else:
            canonical_name = canonical_name.strip()
            if not canonical_name:
                raise ValueError("canonical_name must not be empty")

        if entity_type is None:
            entity_type = existing["entity_type"]
        else:
            entity_type = entity_type.strip()
            if not entity_type:
                raise ValueError("entity_type must not be empty")

        if status is None:
            status = existing["status"]
        else:
            _validate_status(status)

        if confidence is None:
            confidence = existing["confidence"]
        else:
            _validate_confidence(confidence)

        if metadata is None:
            metadata_json = existing["metadata_json"]
        else:
            metadata_json = json.dumps(
                metadata,
                sort_keys=True,
                separators=(",", ":"),
            )

        self.conn.execute(
            """
            UPDATE entities
            SET canonical_name = ?,
                entity_type = ?,
                status = ?,
                confidence = ?,
                metadata_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_id = ?
            """,
            (
                canonical_name,
                entity_type,
                status,
                confidence,
                metadata_json,
                entity_id,
            ),
        )
        self.conn.commit()
        return True


def _validate_confidence(value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _validate_status(value: str) -> None:
    if value not in EntityDAO.VALID_STATUSES:
        raise ValueError(
            f"invalid entity status: {value!r}; "
            f"expected one of {sorted(EntityDAO.VALID_STATUSES)}"
        )


def _row_to_entity(row: sqlite3.Row) -> dict[str, Any]:
    metadata = (
        json.loads(row["metadata_json"])
        if row["metadata_json"] is not None
        else None
    )

    return {
        "entity_id": row["entity_id"],
        "canonical_name": row["canonical_name"],
        "entity_type": row["entity_type"],
        "status": row["status"],
        "confidence": row["confidence"],
        "metadata": metadata,
        "metadata_json": row["metadata_json"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

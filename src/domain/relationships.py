"""Governed relationship model for Mnemosyne's collective knowledge layer.

Phase 10E.1 establishes durable relationship identity and lifecycle metadata.

Relationships are derived collective structures. They do not contain private
memory content. Evidence and extraction are introduced separately so that
relationships remain auditable and rebuildable.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "collective.db"

RELATIONSHIP_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_entity_id TEXT NOT NULL,
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'active',
    relationship_kind TEXT NOT NULL DEFAULT 'explicit',
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(
        subject_entity_id,
        predicate,
        object_entity_id,
        relationship_kind
    )
);

CREATE INDEX IF NOT EXISTS idx_relationships_subject
    ON relationships(subject_entity_id);

CREATE INDEX IF NOT EXISTS idx_relationships_object
    ON relationships(object_entity_id);

CREATE INDEX IF NOT EXISTS idx_relationships_predicate
    ON relationships(predicate);

CREATE INDEX IF NOT EXISTS idx_relationships_status
    ON relationships(status);

CREATE INDEX IF NOT EXISTS idx_relationships_kind
    ON relationships(relationship_kind);
"""


class RelationshipDAO:
    """SQLite repository for governed relationship records.

    This DAO stores relationship metadata only. It does not extract,
    infer, resolve, or otherwise establish relationships on its own.
    """

    VALID_STATUSES = frozenset(
        {"active", "inactive", "revoked", "superseded"}
    )
    VALID_KINDS = frozenset({"explicit", "inferred"})

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
        """Create the relationship schema idempotently."""
        self.conn.executescript(RELATIONSHIP_SCHEMA_SQL)
        self.conn.commit()

    def create(
        self,
        subject_entity_id: str,
        predicate: str,
        object_entity_id: str,
        *,
        confidence: float | None = None,
        status: str = "active",
        relationship_kind: str = "explicit",
        metadata: dict[str, Any] | None = None,
        relationship_id: str | None = None,
    ) -> str:
        """Create a relationship and return its stable identifier."""
        _validate_required_text("subject_entity_id", subject_entity_id)
        _validate_required_text("predicate", predicate)
        _validate_required_text("object_entity_id", object_entity_id)
        _validate_status(status)
        _validate_kind(relationship_kind)
        _validate_confidence(confidence)

        relationship_id = relationship_id or str(uuid.uuid4())
        metadata_json = (
            json.dumps(metadata, sort_keys=True, separators=(",", ":"))
            if metadata is not None
            else None
        )

        try:
            self.conn.execute(
                """
                INSERT INTO relationships (
                    relationship_id,
                    subject_entity_id,
                    predicate,
                    object_entity_id,
                    confidence,
                    status,
                    relationship_kind,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relationship_id,
                    subject_entity_id,
                    predicate,
                    object_entity_id,
                    confidence,
                    status,
                    relationship_kind,
                    metadata_json,
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise

        return relationship_id

    def get(self, relationship_id: str) -> dict[str, Any] | None:
        """Return one relationship as a plain dictionary."""
        row = self.conn.execute(
            "SELECT * FROM relationships WHERE relationship_id = ?",
            (relationship_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_relationship(row)

    def list(
        self,
        *,
        subject_entity_id: str | None = None,
        object_entity_id: str | None = None,
        predicate: str | None = None,
        status: str | None = None,
        relationship_kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return relationships in deterministic identifier order."""
        clauses: list[str] = []
        params: list[Any] = []

        if subject_entity_id is not None:
            _validate_required_text("subject_entity_id", subject_entity_id)
            clauses.append("subject_entity_id = ?")
            params.append(subject_entity_id)

        if object_entity_id is not None:
            _validate_required_text("object_entity_id", object_entity_id)
            clauses.append("object_entity_id = ?")
            params.append(object_entity_id)

        if predicate is not None:
            _validate_required_text("predicate", predicate)
            clauses.append("predicate = ?")
            params.append(predicate)

        if status is not None:
            _validate_status(status)
            clauses.append("status = ?")
            params.append(status)

        if relationship_kind is not None:
            _validate_kind(relationship_kind)
            clauses.append("relationship_kind = ?")
            params.append(relationship_kind)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM relationships
            {where}
            ORDER BY relationship_id
            """,
            params,
        ).fetchall()

        return [_row_to_relationship(row) for row in rows]

    def update(
        self,
        relationship_id: str,
        *,
        confidence: float | None = None,
        status: str | None = None,
        relationship_kind: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update governed relationship metadata.

        Returns False when the relationship does not exist.
        """
        existing = self.get(relationship_id)
        if existing is None:
            return False

        if confidence is None:
            confidence = existing["confidence"]
        else:
            _validate_confidence(confidence)

        if status is None:
            status = existing["status"]
        else:
            _validate_status(status)

        if relationship_kind is None:
            relationship_kind = existing["relationship_kind"]
        else:
            _validate_kind(relationship_kind)

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
            UPDATE relationships
            SET confidence = ?,
                status = ?,
                relationship_kind = ?,
                metadata_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE relationship_id = ?
            """,
            (
                confidence,
                status,
                relationship_kind,
                metadata_json,
                relationship_id,
            ),
        )
        self.conn.commit()
        return True


def _validate_required_text(field: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")


def _validate_confidence(value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _validate_status(value: str) -> None:
    if value not in RelationshipDAO.VALID_STATUSES:
        raise ValueError(
            f"invalid relationship status: {value!r}; "
            f"expected one of {sorted(RelationshipDAO.VALID_STATUSES)}"
        )


def _validate_kind(value: str) -> None:
    if value not in RelationshipDAO.VALID_KINDS:
        raise ValueError(
            f"invalid relationship kind: {value!r}; "
            f"expected one of {sorted(RelationshipDAO.VALID_KINDS)}"
        )


def _row_to_relationship(row: sqlite3.Row) -> dict[str, Any]:
    metadata = (
        json.loads(row["metadata_json"])
        if row["metadata_json"] is not None
        else None
    )

    return {
        "relationship_id": row["relationship_id"],
        "subject_entity_id": row["subject_entity_id"],
        "predicate": row["predicate"],
        "object_entity_id": row["object_entity_id"],
        "confidence": row["confidence"],
        "status": row["status"],
        "relationship_kind": row["relationship_kind"],
        "metadata_json": metadata,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

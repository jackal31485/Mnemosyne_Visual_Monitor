"""Governed entity-resolution decisions for Mnemosyne Phase 10D.

Resolution records connect extracted entity mentions to explicit resolution
decisions.  They do not perform matching or silently merge entities.

Canonical entities remain independent records, and source memory content is
never stored here.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "collective.db"

ENTITY_RESOLUTION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entity_resolutions (
    resolution_id TEXT PRIMARY KEY,
    mention_id TEXT NOT NULL,
    proposed_entity_id TEXT,
    decision TEXT NOT NULL,
    confidence REAL,
    resolution_method TEXT NOT NULL,
    evidence_json TEXT,
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT,
    UNIQUE(mention_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_resolutions_mention
    ON entity_resolutions(mention_id);

CREATE INDEX IF NOT EXISTS idx_entity_resolutions_entity
    ON entity_resolutions(proposed_entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_resolutions_decision
    ON entity_resolutions(decision);
"""


class EntityResolutionDAO:
    """SQLite repository for explicit entity-resolution decisions."""

    VALID_DECISIONS = frozenset(
        {
            "unresolved",
            "same_entity",
            "new_entity",
            "ambiguous",
            "rejected",
        }
    )

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
        self.conn.executescript(ENTITY_RESOLUTION_SCHEMA_SQL)
        self.conn.commit()

    def create(
        self,
        *,
        mention_id: str,
        decision: str,
        resolution_method: str,
        proposed_entity_id: str | None = None,
        confidence: float | None = None,
        evidence: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        resolution_id: str | None = None,
        decided_at: str | None = None,
    ) -> str:
        _validate_required_text("mention_id", mention_id)
        _validate_required_text("resolution_method", resolution_method)
        _validate_decision(decision)
        _validate_confidence(confidence)

        if proposed_entity_id is not None:
            _validate_required_text(
                "proposed_entity_id",
                proposed_entity_id,
            )

        resolution_id = resolution_id or str(uuid.uuid4())

        evidence_json = (
            json.dumps(
                evidence,
                sort_keys=True,
                separators=(",", ":"),
            )
            if evidence is not None
            else None
        )

        metadata_json = (
            json.dumps(
                metadata,
                sort_keys=True,
                separators=(",", ":"),
            )
            if metadata is not None
            else None
        )

        columns = [
            "resolution_id",
            "mention_id",
            "proposed_entity_id",
            "decision",
            "confidence",
            "resolution_method",
            "evidence_json",
            "metadata_json",
        ]

        values: list[Any] = [
            resolution_id,
            mention_id,
            proposed_entity_id,
            decision,
            confidence,
            resolution_method,
            evidence_json,
            metadata_json,
        ]

        if decided_at is not None:
            columns.append("decided_at")
            values.append(decided_at)

        placeholders = ", ".join("?" for _ in values)

        try:
            self.conn.execute(
                f"""
                INSERT INTO entity_resolutions (
                    {", ".join(columns)}
                )
                VALUES ({placeholders})
                """,
                values,
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise

        return resolution_id

    def get(self, resolution_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM entity_resolutions
            WHERE resolution_id = ?
            """,
            (resolution_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_resolution(row)

    def get_for_mention(
        self,
        mention_id: str,
    ) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM entity_resolutions
            WHERE mention_id = ?
            """,
            (mention_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_resolution(row)

    def list(
        self,
        *,
        decision: str | None = None,
        proposed_entity_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        if decision is not None:
            _validate_decision(decision)
            clauses.append("decision = ?")
            params.append(decision)

        if proposed_entity_id is not None:
            _validate_required_text(
                "proposed_entity_id",
                proposed_entity_id,
            )
            clauses.append("proposed_entity_id = ?")
            params.append(proposed_entity_id)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM entity_resolutions
            {where}
            ORDER BY resolution_id
            """,
            params,
        ).fetchall()

        return [_row_to_resolution(row) for row in rows]


def _validate_required_text(field: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")


def _validate_decision(value: str) -> None:
    if value not in EntityResolutionDAO.VALID_DECISIONS:
        raise ValueError(
            f"invalid resolution decision: {value!r}; "
            f"expected one of {sorted(EntityResolutionDAO.VALID_DECISIONS)}"
        )


def _validate_confidence(value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _row_to_resolution(row: sqlite3.Row) -> dict[str, Any]:
    evidence = (
        json.loads(row["evidence_json"])
        if row["evidence_json"] is not None
        else None
    )

    metadata = (
        json.loads(row["metadata_json"])
        if row["metadata_json"] is not None
        else None
    )

    return {
        "resolution_id": row["resolution_id"],
        "mention_id": row["mention_id"],
        "proposed_entity_id": row["proposed_entity_id"],
        "decision": row["decision"],
        "confidence": row["confidence"],
        "resolution_method": row["resolution_method"],
        "evidence": evidence,
        "evidence_json": row["evidence_json"],
        "decided_at": row["decided_at"],
        "metadata": metadata,
        "metadata_json": row["metadata_json"],
    }

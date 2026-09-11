"""Relationship evidence and provenance for Mnemosyne's collective layer.

Phase 10E.2 establishes durable evidence records connecting a relationship
to its authoritative collective source.

Evidence is derived metadata. It must remain auditable and must never contain
private memory content.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "collective.db"

RELATIONSHIP_EVIDENCE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS relationship_evidence (
    evidence_id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    collective_entry_id INTEGER NOT NULL,
    source_memory_id TEXT NOT NULL,
    source_profile TEXT NOT NULL,
    evidence_reference TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    confidence REAL,
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(
        relationship_id,
        collective_entry_id,
        source_memory_id,
        source_profile,
        evidence_reference,
        extraction_method
    )
);

CREATE INDEX IF NOT EXISTS idx_relationship_evidence_relationship
    ON relationship_evidence(relationship_id);

CREATE INDEX IF NOT EXISTS idx_relationship_evidence_collective
    ON relationship_evidence(collective_entry_id);

CREATE INDEX IF NOT EXISTS idx_relationship_evidence_source_memory
    ON relationship_evidence(source_memory_id);

CREATE INDEX IF NOT EXISTS idx_relationship_evidence_source_profile
    ON relationship_evidence(source_profile);
"""


class RelationshipEvidenceDAO:
    """SQLite repository for relationship evidence records.

    Evidence records identify why a relationship is associated with a source.
    The DAO stores provenance metadata only and never stores the underlying
    memory content.
    """

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
        """Create the evidence schema idempotently."""
        self.conn.executescript(RELATIONSHIP_EVIDENCE_SCHEMA_SQL)
        self.conn.commit()

    def add(
        self,
        *,
        relationship_id: str,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
        evidence_reference: str,
        extraction_method: str,
        confidence: float | None = None,
        evidence_id: str | None = None,
        extracted_at: str | None = None,
    ) -> str:
        """Add relationship evidence and return its stable identifier.

        Duplicate evidence is rejected rather than silently creating another
        derived record. This supports deterministic rebuilds.
        """
        _validate_required_text("relationship_id", relationship_id)
        _validate_positive_integer("collective_entry_id", collective_entry_id)
        _validate_required_text("source_memory_id", source_memory_id)
        _validate_required_text("source_profile", source_profile)
        _validate_required_text("evidence_reference", evidence_reference)
        _validate_required_text("extraction_method", extraction_method)
        _validate_confidence(confidence)

        evidence_id = evidence_id or str(uuid.uuid4())

        try:
            if extracted_at is None:
                self.conn.execute(
                    """
                    INSERT INTO relationship_evidence (
                        evidence_id,
                        relationship_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        evidence_reference,
                        extraction_method,
                        confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        relationship_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        evidence_reference,
                        extraction_method,
                        confidence,
                    ),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO relationship_evidence (
                        evidence_id,
                        relationship_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        evidence_reference,
                        extraction_method,
                        confidence,
                        extracted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        relationship_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        evidence_reference,
                        extraction_method,
                        confidence,
                        extracted_at,
                    ),
                )

            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise

        return evidence_id

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        """Return one evidence record as a plain dictionary."""
        row = self.conn.execute(
            """
            SELECT *
            FROM relationship_evidence
            WHERE evidence_id = ?
            """,
            (evidence_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_evidence(row)

    def list(
        self,
        *,
        relationship_id: str | None = None,
        collective_entry_id: int | None = None,
        source_profile: str | None = None,
    ) -> list[dict[str, Any]]:
        """List evidence deterministically."""
        clauses: list[str] = []
        params: list[Any] = []

        if relationship_id is not None:
            _validate_required_text("relationship_id", relationship_id)
            clauses.append("relationship_id = ?")
            params.append(relationship_id)

        if collective_entry_id is not None:
            _validate_positive_integer(
                "collective_entry_id",
                collective_entry_id,
            )
            clauses.append("collective_entry_id = ?")
            params.append(collective_entry_id)

        if source_profile is not None:
            _validate_required_text("source_profile", source_profile)
            clauses.append("source_profile = ?")
            params.append(source_profile)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM relationship_evidence
            {where}
            ORDER BY
                relationship_id,
                collective_entry_id,
                source_profile,
                source_memory_id,
                evidence_id
            """,
            params,
        ).fetchall()

        return [_row_to_evidence(row) for row in rows]


def _validate_required_text(field: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")


def _validate_positive_integer(field: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _validate_confidence(value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _row_to_evidence(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "evidence_id": row["evidence_id"],
        "relationship_id": row["relationship_id"],
        "collective_entry_id": row["collective_entry_id"],
        "source_memory_id": row["source_memory_id"],
        "source_profile": row["source_profile"],
        "evidence_reference": row["evidence_reference"],
        "extraction_method": row["extraction_method"],
        "confidence": row["confidence"],
        "extracted_at": row["extracted_at"],
    }

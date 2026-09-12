"""Governed temporal evidence for Mnemosyne's collective knowledge layer.

Phase 11A establishes the durable evidence model for temporal intelligence.

Temporal evidence is derived metadata. It never stores private source-memory
content. It records what temporal assertion is supported by a governed
collective entry, together with source provenance, precision, confidence, and
extraction metadata.

This layer deliberately does not infer chronology or historical state. Those
operations belong to later Phase 11 stages and must consume this evidence
without rewriting it.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "collective.db"

TEMPORAL_EVIDENCE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS temporal_evidence (
    temporal_evidence_id TEXT PRIMARY KEY,
    collective_entry_id INTEGER NOT NULL,

    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,

    object_type TEXT,
    object_id TEXT,

    temporal_relation TEXT NOT NULL,

    start_time TEXT,
    end_time TEXT,
    precision TEXT NOT NULL,

    confidence REAL,
    evidence_kind TEXT NOT NULL DEFAULT 'observed',
    extraction_method TEXT NOT NULL,

    source_memory_id TEXT NOT NULL,
    source_profile TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        (object_type IS NULL AND object_id IS NULL)
        OR
        (object_type IS NOT NULL AND object_id IS NOT NULL)
    ),
    CHECK (
        start_time IS NULL
        OR end_time IS NULL
        OR start_time <= end_time
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_temporal_evidence_identity
    ON temporal_evidence(
        collective_entry_id,
        subject_type,
        subject_id,
        COALESCE(object_type, ''),
        COALESCE(object_id, ''),
        temporal_relation,
        COALESCE(start_time, ''),
        COALESCE(end_time, ''),
        precision,
        source_memory_id,
        source_profile,
        evidence_kind,
        extraction_method
    );

CREATE INDEX IF NOT EXISTS idx_temporal_evidence_collective
    ON temporal_evidence(collective_entry_id);

CREATE INDEX IF NOT EXISTS idx_temporal_evidence_subject
    ON temporal_evidence(subject_type, subject_id);

CREATE INDEX IF NOT EXISTS idx_temporal_evidence_object
    ON temporal_evidence(object_type, object_id);

CREATE INDEX IF NOT EXISTS idx_temporal_evidence_relation
    ON temporal_evidence(temporal_relation);

CREATE INDEX IF NOT EXISTS idx_temporal_evidence_source_memory
    ON temporal_evidence(source_memory_id);

CREATE INDEX IF NOT EXISTS idx_temporal_evidence_source_profile
    ON temporal_evidence(source_profile);
"""


class TemporalEvidenceDAO:
    """SQLite repository for governed temporal evidence.

    The DAO stores assertions and provenance metadata only. It does not
    extract, infer, resolve, or rewrite temporal state.
    """

    VALID_SUBJECT_TYPES = frozenset({"memory", "entity", "relationship"})
    VALID_EVIDENCE_KINDS = frozenset({"observed", "inferred"})
    VALID_PRECISIONS = frozenset(
        {
            "unknown",
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "second",
        }
    )
    VALID_RELATIONS = frozenset(
        {
            "at",
            "before",
            "after",
            "during",
            "overlaps",
            "meets",
            "starts",
            "ends",
            "ongoing",
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
        """Create the temporal evidence schema idempotently."""
        self.conn.executescript(TEMPORAL_EVIDENCE_SCHEMA_SQL)
        self.conn.commit()

    def add(
        self,
        *,
        collective_entry_id: int,
        subject_type: str,
        subject_id: str,
        temporal_relation: str,
        precision: str,
        extraction_method: str,
        source_memory_id: str,
        source_profile: str,
        object_type: str | None = None,
        object_id: str | None = None,
        start_time: str | datetime | None = None,
        end_time: str | datetime | None = None,
        confidence: float | None = None,
        evidence_kind: str = "observed",
        temporal_evidence_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        """Add one temporal evidence record.

        ``observed`` records must represent explicit source evidence.
        ``inferred`` records are permitted for later reasoning stages but are
        always marked distinctly. No method here converts inferred evidence
        into observed evidence.
        """
        _validate_positive_integer(
            "collective_entry_id",
            collective_entry_id,
        )
        _validate_enum("subject_type", subject_type, self.VALID_SUBJECT_TYPES)
        _validate_required_text("subject_id", subject_id)
        _validate_enum(
            "temporal_relation",
            temporal_relation,
            self.VALID_RELATIONS,
        )
        _validate_enum("precision", precision, self.VALID_PRECISIONS)
        _validate_required_text("extraction_method", extraction_method)
        _validate_required_text("source_memory_id", source_memory_id)
        _validate_required_text("source_profile", source_profile)
        _validate_enum(
            "evidence_kind",
            evidence_kind,
            self.VALID_EVIDENCE_KINDS,
        )
        _validate_confidence(confidence)

        if (object_type is None) != (object_id is None):
            raise ValueError(
                "object_type and object_id must be supplied together"
            )

        if object_type is not None:
            _validate_enum(
                "object_type",
                object_type,
                self.VALID_SUBJECT_TYPES,
            )
            _validate_required_text("object_id", object_id)

        start_value = _normalize_datetime(start_time)
        end_value = _normalize_datetime(end_time)

        if start_value is not None and end_value is not None:
            if start_value > end_value:
                raise ValueError("start_time must not be after end_time")

        if precision == "unknown" and (start_value is not None or end_value is not None):
            raise ValueError(
                "unknown precision cannot carry an explicit temporal bound"
            )

        temporal_evidence_id = temporal_evidence_id or str(uuid.uuid4())

        values = (
            temporal_evidence_id,
            collective_entry_id,
            subject_type,
            subject_id,
            object_type,
            object_id,
            temporal_relation,
            start_value,
            end_value,
            precision,
            confidence,
            evidence_kind,
            extraction_method,
            source_memory_id,
            source_profile,
            created_at,
        )

        try:
            if created_at is None:
                self.conn.execute(
                    """
                    INSERT INTO temporal_evidence (
                        temporal_evidence_id,
                        collective_entry_id,
                        subject_type,
                        subject_id,
                        object_type,
                        object_id,
                        temporal_relation,
                        start_time,
                        end_time,
                        precision,
                        confidence,
                        evidence_kind,
                        extraction_method,
                        source_memory_id,
                        source_profile
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values[:-1],
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO temporal_evidence (
                        temporal_evidence_id,
                        collective_entry_id,
                        subject_type,
                        subject_id,
                        object_type,
                        object_id,
                        temporal_relation,
                        start_time,
                        end_time,
                        precision,
                        confidence,
                        evidence_kind,
                        extraction_method,
                        source_memory_id,
                        source_profile,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise

        return temporal_evidence_id

    def get(self, temporal_evidence_id: str) -> dict[str, Any] | None:
        """Return one temporal evidence record."""
        row = self.conn.execute(
            """
            SELECT *
            FROM temporal_evidence
            WHERE temporal_evidence_id = ?
            """,
            (temporal_evidence_id,),
        ).fetchone()

        return _row_to_evidence(row) if row is not None else None

    def list(
        self,
        *,
        collective_entry_id: int | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        temporal_relation: str | None = None,
        evidence_kind: str | None = None,
        source_profile: str | None = None,
    ) -> list[dict[str, Any]]:
        """List evidence deterministically with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []

        if collective_entry_id is not None:
            _validate_positive_integer(
                "collective_entry_id",
                collective_entry_id,
            )
            clauses.append("collective_entry_id = ?")
            params.append(collective_entry_id)

        if subject_type is not None:
            _validate_enum("subject_type", subject_type, self.VALID_SUBJECT_TYPES)
            clauses.append("subject_type = ?")
            params.append(subject_type)

        if subject_id is not None:
            _validate_required_text("subject_id", subject_id)
            clauses.append("subject_id = ?")
            params.append(subject_id)

        if temporal_relation is not None:
            _validate_enum(
                "temporal_relation",
                temporal_relation,
                self.VALID_RELATIONS,
            )
            clauses.append("temporal_relation = ?")
            params.append(temporal_relation)

        if evidence_kind is not None:
            _validate_enum(
                "evidence_kind",
                evidence_kind,
                self.VALID_EVIDENCE_KINDS,
            )
            clauses.append("evidence_kind = ?")
            params.append(evidence_kind)

        if source_profile is not None:
            _validate_required_text("source_profile", source_profile)
            clauses.append("source_profile = ?")
            params.append(source_profile)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM temporal_evidence
            {where}
            ORDER BY
                collective_entry_id,
                subject_type,
                subject_id,
                temporal_relation,
                COALESCE(start_time, ''),
                COALESCE(end_time, ''),
                source_profile,
                source_memory_id,
                temporal_evidence_id
            """,
            params,
        ).fetchall()

        return [_row_to_evidence(row) for row in rows]


def _normalize_datetime(value: str | datetime | None) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
        return None

    raise TypeError("temporal bounds must be strings, datetimes, or None")


def _validate_required_text(field: str, value: str | None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")


def _validate_positive_integer(field: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _validate_confidence(value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _validate_enum(
    field: str,
    value: str,
    allowed: frozenset[str],
) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(
            f"{field} must be one of {sorted(allowed)!r}"
        )


def _row_to_evidence(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "temporal_evidence_id": row["temporal_evidence_id"],
        "collective_entry_id": row["collective_entry_id"],
        "subject_type": row["subject_type"],
        "subject_id": row["subject_id"],
        "object_type": row["object_type"],
        "object_id": row["object_id"],
        "temporal_relation": row["temporal_relation"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "precision": row["precision"],
        "confidence": row["confidence"],
        "evidence_kind": row["evidence_kind"],
        "extraction_method": row["extraction_method"],
        "source_memory_id": row["source_memory_id"],
        "source_profile": row["source_profile"],
        "created_at": row["created_at"],
    }

"""Entity mention persistence for Mnemosyne Phase 10B.

Entity mentions are extraction results, not canonical entities.

This layer deliberately preserves source provenance and qualified profile
identity while remaining independent from entity resolution.  Canonical
entities are created/resolved later by Phase 10D.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "collective.db"

ENTITY_MENTION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entity_mentions (
    mention_id TEXT PRIMARY KEY,
    collective_entry_id INTEGER NOT NULL,
    source_memory_id TEXT NOT NULL,
    source_profile TEXT NOT NULL,
    mention_text TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    confidence REAL,
    extraction_method TEXT NOT NULL,
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(
        collective_entry_id,
        source_memory_id,
        source_profile,
        mention_text,
        entity_type,
        extraction_method
    )
);

CREATE INDEX IF NOT EXISTS idx_entity_mentions_collective
    ON entity_mentions(collective_entry_id);

CREATE INDEX IF NOT EXISTS idx_entity_mentions_source_memory
    ON entity_mentions(source_memory_id);

CREATE INDEX IF NOT EXISTS idx_entity_mentions_source_profile
    ON entity_mentions(source_profile);

CREATE INDEX IF NOT EXISTS idx_entity_mentions_type
    ON entity_mentions(entity_type);
"""


class EntityMentionDAO:
    """SQLite repository for extracted entity mentions."""

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
        self.conn.executescript(ENTITY_MENTION_SCHEMA_SQL)
        self.conn.commit()

    def add(
        self,
        *,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
        mention_text: str,
        entity_type: str,
        extraction_method: str,
        confidence: float | None = None,
        mention_id: str | None = None,
        extracted_at: str | None = None,
    ) -> str:
        _validate_positive_integer(
            "collective_entry_id",
            collective_entry_id,
        )
        _validate_required_text("source_memory_id", source_memory_id)
        _validate_required_text("source_profile", source_profile)
        _validate_required_text("mention_text", mention_text)
        _validate_required_text("entity_type", entity_type)
        _validate_required_text("extraction_method", extraction_method)
        _validate_confidence(confidence)

        mention_id = mention_id or str(uuid.uuid4())

        try:
            if extracted_at is None:
                self.conn.execute(
                    """
                    INSERT INTO entity_mentions (
                        mention_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        mention_text,
                        entity_type,
                        confidence,
                        extraction_method
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mention_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        mention_text,
                        entity_type,
                        confidence,
                        extraction_method,
                    ),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO entity_mentions (
                        mention_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        mention_text,
                        entity_type,
                        confidence,
                        extraction_method,
                        extracted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mention_id,
                        collective_entry_id,
                        source_memory_id,
                        source_profile,
                        mention_text,
                        entity_type,
                        confidence,
                        extraction_method,
                        extracted_at,
                    ),
                )

            self.conn.commit()

        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise

        return mention_id

    def get(self, mention_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM entity_mentions
            WHERE mention_id = ?
            """,
            (mention_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_mention(row)

    def list(
        self,
        *,
        collective_entry_id: int | None = None,
        source_profile: str | None = None,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []

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

        if entity_type is not None:
            _validate_required_text("entity_type", entity_type)
            clauses.append("entity_type = ?")
            params.append(entity_type)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM entity_mentions
            {where}
            ORDER BY
                collective_entry_id,
                source_profile,
                source_memory_id,
                mention_text,
                entity_type,
                extraction_method,
                mention_id
            """,
            params,
        ).fetchall()

        return [_row_to_mention(row) for row in rows]


def _validate_required_text(field: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")


def _validate_positive_integer(field: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _validate_confidence(value: float | None) -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _row_to_mention(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "mention_id": row["mention_id"],
        "collective_entry_id": row["collective_entry_id"],
        "source_memory_id": row["source_memory_id"],
        "source_profile": row["source_profile"],
        "mention_text": row["mention_text"],
        "entity_type": row["entity_type"],
        "confidence": row["confidence"],
        "extraction_method": row["extraction_method"],
        "extracted_at": row["extracted_at"],
    }

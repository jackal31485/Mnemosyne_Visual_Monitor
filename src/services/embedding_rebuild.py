"""Atomic rebuild of collective semantic embeddings.

This service intentionally differs from ``embedding_backfill``:

* backfill() only fills NULL embeddings;
* rebuild_embeddings() explicitly replaces existing embeddings;
* production callers provide the encoder;
* all database updates occur inside one SQLite transaction.

The collective database remains authoritative for lifecycle state and
source identity. Source memory content is retrieved exclusively through
MemoryGateway.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

import numpy as np

from src.domain.collective import CollectiveDAO
from src.domain.embedding_generator import DEFAULT_DIMENSIONS, decode_embedding
from src.domain.memory_gateway import MemoryGateway


class EmbeddingEncoder(Protocol):
    """Minimal encoder contract required by the rebuild operation."""

    def generate(self, sanitized: str) -> bytes:
        """Return a serialized float32 embedding."""
        ...


@dataclass(frozen=True)
class EmbeddingRebuildFailure:
    """A source memory that prevented the rebuild from completing."""

    entry_id: int
    source_profile: str
    origin_memory_id: str
    reason: str


@dataclass(frozen=True)
class EmbeddingRebuildReport:
    """Deterministic summary of an embedding rebuild."""

    processed: int
    updated: int
    failures: tuple[EmbeddingRebuildFailure, ...]


def _validate_embedding(embedding: bytes) -> bytes:
    """Validate an encoder result before it reaches SQLite."""

    if not isinstance(embedding, (bytes, bytearray, memoryview)):
        raise TypeError("encoder must return a bytes-like embedding")

    blob = bytes(embedding)

    try:
        vector = decode_embedding(blob)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"encoder returned invalid embedding: {exc}") from exc

    array = np.asarray(vector, dtype=np.float32)

    if array.shape != (DEFAULT_DIMENSIONS,):
        raise ValueError(
            f"encoder returned {array.shape[0]} dimensions; "
            f"expected {DEFAULT_DIMENSIONS}"
        )

    if not np.all(np.isfinite(array)):
        raise ValueError("encoder returned non-finite embedding values")

    norm = float(np.linalg.norm(array))

    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError("encoder returned a zero-norm embedding")

    return blob


def rebuild_embeddings(
    dao: CollectiveDAO,
    gateway: MemoryGateway,
    encoder: EmbeddingEncoder,
) -> EmbeddingRebuildReport:
    """Atomically replace embeddings for all eligible collective entries.

    Eligible entries are promoted and non-revoked. Entries are processed in
    ascending ID order for deterministic behavior.

    Any source-memory or encoder failure aborts the complete operation and
    rolls back every embedding update.
    """

    rows = dao.conn.execute(
        """
        SELECT id, source_profile, origin_memory_id
        FROM collective_entries
        WHERE is_promoted = 1
          AND is_revoked = 0
        ORDER BY id ASC
        """
    ).fetchall()

    updates: list[tuple[bytes, int]] = []
    failures: list[EmbeddingRebuildFailure] = []

    try:
        for row in rows:
            entry_id = int(row["id"])
            source_profile = str(row["source_profile"])
            origin_memory_id = str(row["origin_memory_id"])

            try:
                content = gateway.get_memory(
                    source_profile,
                    origin_memory_id,
                )
            except KeyError as exc:
                failures.append(
                    EmbeddingRebuildFailure(
                        entry_id=entry_id,
                        source_profile=source_profile,
                        origin_memory_id=origin_memory_id,
                        reason=f"missing source memory: {exc}",
                    )
                )
                raise RuntimeError(
                    f"cannot rebuild entry {entry_id}: source memory unavailable"
                ) from exc

            try:
                embedding = _validate_embedding(
                    encoder.generate(content)
                )
            except Exception as exc:
                failures.append(
                    EmbeddingRebuildFailure(
                        entry_id=entry_id,
                        source_profile=source_profile,
                        origin_memory_id=origin_memory_id,
                        reason=str(exc),
                    )
                )
                raise RuntimeError(
                    f"cannot rebuild entry {entry_id}: encoder failure"
                ) from exc

            updates.append((embedding, entry_id))

        dao.conn.execute("BEGIN")

        for embedding, entry_id in updates:
            dao.conn.execute(
                """
                UPDATE collective_entries
                SET embedding = ?
                WHERE id = ?
                """,
                (embedding, entry_id),
            )

        dao.conn.commit()

    except Exception:
        if dao.conn.in_transaction:
            dao.conn.rollback()
        raise

    return EmbeddingRebuildReport(
        processed=len(rows),
        updated=len(updates),
        failures=tuple(failures),
    )

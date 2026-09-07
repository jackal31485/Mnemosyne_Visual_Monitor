from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.domain.collective import CollectiveDAO
from src.domain.memory_gateway import MemoryGateway


DEFAULT_RETRIEVAL_DB = Path("data") / "retrieval.db"
FTS_TABLE = "memory_fts"


@dataclass(frozen=True)
class KeywordIndexResult:
    indexed: int
    skipped: int
    failed: int


class KeywordIndexer:
    """Build and maintain the Phase 8A lexical retrieval index.

    The retrieval index is deliberately separate from collective.db.

    collective.db remains authoritative for:
      - promotion
      - revocation
      - provenance
      - source identity

    retrieval.db is a rebuildable search cache containing content obtained
    through MemoryGateway.
    """

    def __init__(
        self,
        dao: CollectiveDAO,
        gateway: MemoryGateway,
        db_path: str | Path | None = None,
    ) -> None:
        self.dao = dao
        self.gateway = gateway
        self.db_path = Path(
            db_path or DEFAULT_RETRIEVAL_DB
        ).absolute()

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
            )
            self._conn.row_factory = sqlite3.Row

        return self._conn

    def ensure_schema(self) -> None:
        """Create the retrieval FTS5 schema."""

        self.conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
            USING fts5(
                entry_id UNINDEXED,
                source_profile UNINDEXED,
                origin_memory_id UNINDEXED,
                content,
                tokenize='porter'
            )
            """
        )

        self.conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def rebuild(self) -> KeywordIndexResult:
        """Rebuild the entire lexical index.

        Only currently promoted, non-revoked collective entries are indexed.
        """

        self.ensure_schema()

        self.conn.execute(
            "DELETE FROM memory_fts"
        )

        rows = self.dao.conn.execute(
            """
            SELECT
                id,
                source_profile,
                origin_memory_id
            FROM collective_entries
            WHERE is_promoted = 1
              AND is_revoked = 0
            ORDER BY id
            """
        ).fetchall()

        indexed = 0
        skipped = 0
        failed = 0

        for row in rows:
            entry_id = int(row["id"])
            profile = str(row["source_profile"])
            memory_id = str(row["origin_memory_id"])

            try:
                content = self.gateway.get_memory(
                    profile,
                    memory_id,
                )

                if not isinstance(content, str):
                    skipped += 1
                    continue

                if not content.strip():
                    skipped += 1
                    continue

                self.conn.execute(
                    """
                    INSERT INTO memory_fts(
                        entry_id,
                        source_profile,
                        origin_memory_id,
                        content
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        profile,
                        memory_id,
                        content,
                    ),
                )

                indexed += 1

            except (KeyError, OSError, sqlite3.Error):
                skipped += 1

            except Exception:
                failed += 1

        self.conn.commit()

        return KeywordIndexResult(
            indexed=indexed,
            skipped=skipped,
            failed=failed,
        )

    def index_entry(self, entry_id: int) -> bool:
        """Index one eligible collective entry."""

        self.ensure_schema()

        row = self.dao.conn.execute(
            """
            SELECT
                id,
                source_profile,
                origin_memory_id,
                is_promoted,
                is_revoked
            FROM collective_entries
            WHERE id = ?
            LIMIT 1
            """,
            (entry_id,),
        ).fetchone()

        if row is None:
            return False

        self.conn.execute(
            "DELETE FROM memory_fts WHERE entry_id = ?",
            (entry_id,),
        )

        if not row["is_promoted"] or row["is_revoked"]:
            self.conn.commit()
            return False

        profile = str(row["source_profile"])
        memory_id = str(row["origin_memory_id"])

        try:
            content = self.gateway.get_memory(
                profile,
                memory_id,
            )
        except (KeyError, OSError):
            self.conn.commit()
            return False

        if not isinstance(content, str) or not content.strip():
            self.conn.commit()
            return False

        self.conn.execute(
            """
            INSERT INTO memory_fts(
                entry_id,
                source_profile,
                origin_memory_id,
                content
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                entry_id,
                profile,
                memory_id,
                content,
            ),
        )

        self.conn.commit()

        return True

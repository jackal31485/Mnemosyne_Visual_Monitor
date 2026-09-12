from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.collective import CollectiveDAO


DEFAULT_RETRIEVAL_DB = Path("data") / "retrieval.db"


@dataclass(frozen=True)
class KeywordResult:
    """A lexical retrieval result."""

    entry_id: int
    source_profile: str
    origin_memory_id: str
    score: float
    provenance: List[Dict[str, str]]


class KeywordSearcher:
    """SQLite FTS5/BM25 lexical retrieval.

    The FTS index is a rebuildable retrieval cache.

    Lifecycle authorization always comes from collective.db.
    """

    def __init__(
        self,
        dao: CollectiveDAO,
        db_path: str | Path | None = None,
    ) -> None:
        self.dao = dao
        self.db_path = Path(
            db_path or DEFAULT_RETRIEVAL_DB
        ).absolute()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_collective(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.dao._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        return conn


    def close(self) -> None:
        """Retained for lifecycle compatibility.

        Search connections are now scoped to individual search calls, so
        there is no persistent connection to close.
        """
        return None

    def _build_match_expr(self, query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        terms = query.strip().split()
        if not terms:
            return ""

        # Treat caller input as ordinary natural-language search text,
        # not as raw FTS5 syntax. Strip punctuation from each token and
        # explicitly OR the resulting terms so natural-language queries
        # do not require every query word to be present.
        safe_terms = []

        for term in terms:
            cleaned = "".join(
                character
                for character in term
                if character.isalnum() or character == "_"
            )
            if not cleaned:
                continue

            safe_terms.append(
                '"' + cleaned.replace('"', '""') + '"'
            )

        return " OR ".join(safe_terms)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        profile: Optional[str] = None,
    ) -> List[KeywordResult]:
        """Return BM25-ranked lexical results.

        Search candidates come from retrieval.db.

        Promotion/revocation state is subsequently checked against the
        authoritative collective.db.
        """

        if limit <= 0:
            return []

        match_expr = self._build_match_expr(query)

        if not match_expr:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    entry_id,
                    source_profile,
                    origin_memory_id,
                    bm25(memory_fts) AS score
                FROM memory_fts
                WHERE memory_fts MATCH ?
                ORDER BY bm25(memory_fts) ASC, entry_id ASC
                LIMIT ?
                """,
                (
                    match_expr,
                    limit * 4,
                ),
            ).fetchall()

        results: List[KeywordResult] = []

        for row in rows:
            entry_id = int(row["entry_id"])

            with self._connect_collective() as collective_conn:
                authoritative = collective_conn.execute(
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

                if authoritative is None:
                    continue

                if not authoritative["is_promoted"]:
                    continue

                if authoritative["is_revoked"]:
                    continue

                if (
                    profile is not None
                    and authoritative["source_profile"] != profile
                ):
                    continue

                provenance_rows = collective_conn.execute(
                    """
                    SELECT
                        source_profile,
                        origin_memory_id,
                        created_at
                    FROM collective_provenance
                    WHERE collective_entry_id = ?
                    ORDER BY source_profile, origin_memory_id
                    """,
                    (entry_id,),
                ).fetchall()

            provenance = [
                dict(r)
                for r in provenance_rows
            ]

            results.append(
                KeywordResult(
                    entry_id=entry_id,
                    source_profile=str(
                        authoritative["source_profile"]
                    ),
                    origin_memory_id=str(
                        authoritative["origin_memory_id"]
                    ),
                    score=float(row["score"]),
                    provenance=provenance,
                )
            )

            if len(results) >= limit:
                break

        return results

def get_searcher(
    dao: CollectiveDAO,
    db_path: str | Path | None = None,
) -> KeywordSearcher:
    return KeywordSearcher(
        dao,
        db_path=db_path,
    )

from __future__ import annotations

from src.retrieval.semantic_search import SemanticSearcher
from src.retrieval.hybrid_search import HybridRetrievalService, HybridResult

from dataclasses import dataclass
from datetime import datetime
import math
import numpy as np
from typing import Optional, List, Tuple

from .athena_interface import AthenaCollectiveInterface

# ---------------------------------------------------------------------------
# Read‑only Athena API – thin wrapper around AthenaCollectiveInterface.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SanitizedMemory:
    """Placeholder for a sanitized summary of a private Mnemosyne memory.

    The real gateway will provide a meaningful title/abstract.  Until then the
    fields contain static markers so that callers can rely on a stable type.
    """
    id: str
    title: str
    abstract: str


class AthenaAPI:
    def __init__(
        self,
        interface: AthenaCollectiveInterface | None = None,
        hybrid_service: HybridRetrievalService | None = None,
    ) -> None:
        # Dependency injection – default to the global singleton style used in tests.
        self._iface = interface or AthenaCollectiveInterface()
        self._hybrid_service = hybrid_service

    def get_entry(self, entry_id: int) -> Tuple[int, ...] | None:
        """Return a promoted & not‑revoked collective tuple; otherwise ``None``."""
        return self._iface.get_by_id(entry_id)

    def list_entries(self, profile: str | None = None) -> List[int]:
        ids = self._iface.list_promoted()
        if profile is None:
            return ids
        # Filter by source_profile using the underlying DAO because the interface has no filter.
        filtered: List[int] = []
        for eid in ids:
            row = self._iface.get_by_id(eid)
            if row and row[1] == profile:
                filtered.append(eid)
        return filtered

    # ------------------------------------------------------------------
    # Phase 5C – similarity search by embedding.
    # ------------------------------------------------------------------
    def search_semantic(
        self,
        vector: List[float],
        top_k: int = 10,
        profile: str | None = None,
    ):
        """Return rich, governed semantic retrieval results."""
        searcher = SemanticSearcher(self._iface._dao)
        return searcher.search(vector, top_k=top_k, profile=profile)

    def search_hybrid(
        self,
        query: str,
        *,
        top_k: int = 10,
        candidate_limit: int = 20,
        keyword_limit: int = 20,
        semantic_limit: int = 20,
        graph_seed_limit: int = 5,
        graph_limit_per_seed: int = 4,
        profile: str | None = None,
        temporal_mode: str | None = None,
        temporal_start: datetime | None = None,
        temporal_end: datetime | None = None,
        reference_time: datetime | None = None,
        rerank: bool = True,
) -> List[HybridResult]:
        """Return unified governed hybrid retrieval results.

        The production retrieval service is injected so model loading and
        expensive retrieval dependencies are not recreated per query.
        """
        if self._hybrid_service is None:
            raise RuntimeError(
                "hybrid retrieval service is not configured"
            )

        return self._hybrid_service.search(
            query,
            top_k=top_k,
            candidate_limit=candidate_limit,
            keyword_limit=keyword_limit,
            semantic_limit=semantic_limit,
            graph_seed_limit=graph_seed_limit,
            graph_limit_per_seed=graph_limit_per_seed,
            profile=profile,
            temporal_mode=temporal_mode,
            temporal_start=temporal_start,
            temporal_end=temporal_end,
            reference_time=reference_time,
            rerank=rerank,
        )

    def search_by_embedding(self, vector: List[float], top_n: int) -> List[int]:
        """Return semantic matches using the historical Athena contract.

        Phase 8B adds :meth:`search_semantic` as the strict, production
        semantic retrieval surface. This legacy method intentionally retains
        the historical behavior used by existing callers and tests, including
        arbitrary embedding dimensions and zero-vector handling.
        """
        if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
            raise ValueError("top_n must be a positive integer")

        try:
            values = [float(value) for value in vector]
        except (TypeError, ValueError):
            raise ValueError("query embedding must contain numeric values")

        if not values:
            raise ValueError("query embedding cannot be empty")

        query = np.asarray(values, dtype=np.float32)

        if not np.all(np.isfinite(query)):
            raise ValueError("query embedding must contain only finite values")

        query_norm = float(np.linalg.norm(query))

        rows = self._iface._dao.conn.execute(
            """
            SELECT id, embedding
            FROM collective_entries
            WHERE is_promoted = 1
              AND is_revoked = 0
            ORDER BY id ASC
            """
        ).fetchall()

        # Preserve the historical zero-vector behavior.
        if query_norm == 0.0:
            zero_vectors = []
            other_vectors = []

            for row in rows:
                blob = row["embedding"]
                if blob is None:
                    continue

                try:
                    candidate = np.frombuffer(blob, dtype=np.float32)
                except (TypeError, ValueError):
                    continue

                if candidate.size != query.size:
                    continue
                if not np.all(np.isfinite(candidate)):
                    continue

                candidate_norm = float(np.linalg.norm(candidate))

                if candidate_norm == 0.0:
                    zero_vectors.append(int(row["id"]))
                else:
                    other_vectors.append(int(row["id"]))

            return (zero_vectors + other_vectors)[:top_n]

        results = []

        for row in rows:
            blob = row["embedding"]
            if blob is None:
                continue

            try:
                candidate = np.frombuffer(blob, dtype=np.float32)
            except (TypeError, ValueError):
                continue

            if candidate.size != query.size:
                continue
            if not np.all(np.isfinite(candidate)):
                continue

            candidate_norm = float(np.linalg.norm(candidate))
            if candidate_norm == 0.0:
                continue

            similarity = float(
                np.dot(query, candidate)
                / (query_norm * candidate_norm)
            )

            if not math.isfinite(similarity):
                continue

            results.append((similarity, int(row["id"])))

        results.sort(key=lambda item: (-item[0], item[1]))

        return [entry_id for _, entry_id in results[:top_n]]

    def find_by_source(self, src: str, orig_mem: str) -> Tuple[int, ...] | None:
        return self._iface.find_by_source(src, orig_mem)

    def resolve_memory(self, origin_memory_id: str) -> SanitizedMemory | None:
        # Find a promoted, non‑revoked entry that references this origin id.
        for eid in self._iface.list_promoted():
            row = self._iface.get_by_id(eid)
            if row and row[2] == origin_memory_id:
                # entry found – return placeholder payload
                return SanitizedMemory(
                    id=str(eid),
                    title="[placeholder title]",
                    abstract="[placeholder abstract]"
                )
        return None

# End of file

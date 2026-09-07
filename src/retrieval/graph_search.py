from dataclasses import dataclass
from typing import List, Optional, Sequence

from src.domain.collective import CollectiveDAO
from src.domain.graph_aggregator import GraphAggregator


@dataclass(frozen=True)
class GraphResult:
    entry_id: int
    source_profile: str
    origin_memory_id: str
    graph_score: float
    provenance: object


class GraphSearcher:
    """Bounded graph expansion over authoritative collective entries.

    This phase performs discovery only. It does not fuse graph scores with
    semantic or keyword scores. Score fusion belongs to Phase 8E.
    """

    def __init__(
        self,
        dao: CollectiveDAO,
        graph: GraphAggregator,
    ) -> None:
        self.dao = dao
        self.graph = graph

    def expand(
        self,
        seed_entry_ids: Sequence[int],
        limit_per_seed: Optional[int] = None,
        profile: Optional[str] = None,
    ) -> List[GraphResult]:
        """Return authorized one-hop graph neighbors for seed entries."""

        if limit_per_seed is not None:
            if (
                not isinstance(limit_per_seed, int)
                or isinstance(limit_per_seed, bool)
                or limit_per_seed < 1
            ):
                raise ValueError("limit_per_seed must be a positive integer")

        seen: set[int] = set()
        results: List[GraphResult] = []

        for raw_seed_id in seed_entry_ids:
            try:
                seed_id = int(raw_seed_id)
            except (TypeError, ValueError):
                raise ValueError("seed_entry_ids must contain integers")

            for entry_id, score in self.graph.get_neighbor_entries(
                seed_id,
                limit=limit_per_seed,
            ):
                entry_id = int(entry_id)

                if entry_id in seen:
                    continue

                record = self.dao.get_by_id(entry_id)

                if record is None:
                    continue

                (
                    _record_id,
                    source_profile,
                    origin_memory_id,
                    _proposed_at,
                    _validated_at,
                    _validation_score,
                    _validator_profile,
                    is_revoked,
                    _revocation_reason,
                ) = record

                if is_revoked:
                    continue

                lifecycle_state = self.dao.get_lifecycle_state(entry_id)

                if not lifecycle_state or lifecycle_state[1]:
                    continue

                if profile is not None and source_profile != profile:
                    continue

                provenance = self.dao.get_provenance(entry_id)

                seen.add(entry_id)

                results.append(
                    GraphResult(
                        entry_id=entry_id,
                        source_profile=source_profile,
                        origin_memory_id=origin_memory_id,
                        graph_score=float(score),
                        provenance=provenance,
                    )
                )

        results.sort(
            key=lambda result: (-result.graph_score, result.entry_id)
        )

        return results

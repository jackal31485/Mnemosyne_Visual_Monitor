from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class FusedResult:
    """A deterministic multi-channel retrieval result."""

    entry_id: int
    source_profile: str
    origin_memory_id: str
    fused_score: float

    keyword_rank: int | None
    semantic_rank: int | None
    graph_rank: int | None
    temporal_rank: int | None
    entity_rank: int | None

    keyword_contribution: float
    semantic_contribution: float
    graph_contribution: float
    temporal_contribution: float
    entity_contribution: float

    provenance: Any


class RankFusion:
    """Fuse independently ranked retrieval channels using RRF.

    The fusion layer consumes already-ranked results. It does not query
    databases, inspect embeddings, or interpret channel-specific scores.

    RRF contribution:

        weight / (k + rank)

    where rank is one-based.

    Entity retrieval is an additive fifth channel. Omitting entity results
    preserves the existing four-channel behavior.
    """

    def __init__(
        self,
        *,
        k: int = 60,
        keyword_weight: float = 1.0,
        semantic_weight: float = 1.0,
        graph_weight: float = 1.0,
        temporal_weight: float = 1.0,
        entity_weight: float = 1.0,
    ) -> None:
        if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
            raise ValueError("k must be a positive integer")

        weights = {
            "keyword": keyword_weight,
            "semantic": semantic_weight,
            "graph": graph_weight,
            "temporal": temporal_weight,
            "entity": entity_weight,
        }

        for name, weight in weights.items():
            if (
                not isinstance(weight, (int, float))
                or isinstance(weight, bool)
                or weight < 0
            ):
                raise ValueError(f"{name}_weight must be non-negative")

        self.k = k
        self.keyword_weight = float(keyword_weight)
        self.semantic_weight = float(semantic_weight)
        self.graph_weight = float(graph_weight)
        self.temporal_weight = float(temporal_weight)
        self.entity_weight = float(entity_weight)

    @staticmethod
    def _index_channel(
        results: Sequence[Any],
    ) -> dict[int, tuple[int, Any]]:
        """Return each entry's first one-based rank and result."""

        indexed: dict[int, tuple[int, Any]] = {}
        rank = 0

        for result in results:
            entry_id = int(result.entry_id)

            if entry_id in indexed:
                continue

            rank += 1
            indexed[entry_id] = (rank, result)

        return indexed

    def _contribution(
        self,
        rank: int | None,
        weight: float,
    ) -> float:
        if rank is None or weight == 0.0:
            return 0.0

        return weight / (self.k + rank)

    def fuse(
        self,
        *,
        keyword_results: Sequence[Any] | None = None,
        semantic_results: Sequence[Any] | None = None,
        graph_results: Sequence[Any] | None = None,
        temporal_results: Sequence[Any] | None = None,
        entity_results: Sequence[Any] | None = None,
        top_k: int | None = None,
    ) -> list[FusedResult]:
        """Fuse ranked retrieval results from all available channels."""

        if top_k is not None:
            if (
                not isinstance(top_k, int)
                or isinstance(top_k, bool)
                or top_k < 1
            ):
                raise ValueError("top_k must be a positive integer")

        channels = {
            "keyword": self._index_channel(keyword_results or ()),
            "semantic": self._index_channel(semantic_results or ()),
            "graph": self._index_channel(graph_results or ()),
            "temporal": self._index_channel(temporal_results or ()),
            "entity": self._index_channel(entity_results or ()),
        }

        all_entry_ids: set[int] = set()

        for channel in channels.values():
            all_entry_ids.update(channel)

        fused: list[FusedResult] = []

        for entry_id in all_entry_ids:
            keyword_item = channels["keyword"].get(entry_id)
            semantic_item = channels["semantic"].get(entry_id)
            graph_item = channels["graph"].get(entry_id)
            temporal_item = channels["temporal"].get(entry_id)
            entity_item = channels["entity"].get(entry_id)

            keyword_rank = (
                keyword_item[0] if keyword_item is not None else None
            )
            semantic_rank = (
                semantic_item[0] if semantic_item is not None else None
            )
            graph_rank = (
                graph_item[0] if graph_item is not None else None
            )
            temporal_rank = (
                temporal_item[0] if temporal_item is not None else None
            )
            entity_rank = (
                entity_item[0] if entity_item is not None else None
            )

            keyword_contribution = self._contribution(
                keyword_rank,
                self.keyword_weight,
            )
            semantic_contribution = self._contribution(
                semantic_rank,
                self.semantic_weight,
            )
            graph_contribution = self._contribution(
                graph_rank,
                self.graph_weight,
            )
            temporal_contribution = self._contribution(
                temporal_rank,
                self.temporal_weight,
            )
            entity_contribution = self._contribution(
                entity_rank,
                self.entity_weight,
            )

            canonical_item = next(
                item
                for item in (
                    keyword_item,
                    semantic_item,
                    graph_item,
                    temporal_item,
                    entity_item,
                )
                if item is not None
            )

            result = canonical_item[1]

            fused.append(
                FusedResult(
                    entry_id=entry_id,
                    source_profile=str(result.source_profile),
                    origin_memory_id=str(result.origin_memory_id),
                    fused_score=(
                        keyword_contribution
                        + semantic_contribution
                        + graph_contribution
                        + temporal_contribution
                        + entity_contribution
                    ),
                    keyword_rank=keyword_rank,
                    semantic_rank=semantic_rank,
                    graph_rank=graph_rank,
                    temporal_rank=temporal_rank,
                    entity_rank=entity_rank,
                    keyword_contribution=keyword_contribution,
                    semantic_contribution=semantic_contribution,
                    graph_contribution=graph_contribution,
                    temporal_contribution=temporal_contribution,
                    entity_contribution=entity_contribution,
                    provenance=result.provenance,
                )
            )

        fused.sort(
            key=lambda result: (
                -result.fused_score,
                result.entry_id,
            )
        )

        if top_k is not None:
            return fused[:top_k]

        return fused

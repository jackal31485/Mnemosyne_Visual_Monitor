"""Deterministic explanations for hybrid retrieval results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.retrieval.rank_fusion import FusedResult
from src.retrieval.reranker import RerankedResult


@dataclass(frozen=True)
class RetrievalExplanation:
    """Explain the evidence carried by a fused or reranked result."""

    entry_id: int
    source_profile: str
    origin_memory_id: str

    keyword_rank: int | None
    keyword_contribution: float

    semantic_rank: int | None
    semantic_contribution: float

    graph_rank: int | None
    graph_contribution: float

    temporal_rank: int | None
    temporal_contribution: float

    fused_score: float
    fused_rank: int

    reranker_score: float | None
    reranker_rank: int | None
    rank_change: int | None

    provenance: object


def explain_fused(
    results: Sequence[FusedResult],
) -> list[RetrievalExplanation]:
    """Explain an ordered fused-result sequence.

    The supplied sequence defines the fused rank. No rank is inferred
    from the fused score.
    """

    return [
        RetrievalExplanation(
            entry_id=result.entry_id,
            source_profile=result.source_profile,
            origin_memory_id=result.origin_memory_id,
            keyword_rank=result.keyword_rank,
            keyword_contribution=result.keyword_contribution,
            semantic_rank=result.semantic_rank,
            semantic_contribution=result.semantic_contribution,
            graph_rank=result.graph_rank,
            graph_contribution=result.graph_contribution,
            temporal_rank=result.temporal_rank,
            temporal_contribution=result.temporal_contribution,
            fused_score=result.fused_score,
            fused_rank=rank,
            reranker_score=None,
            reranker_rank=None,
            rank_change=None,
            provenance=result.provenance,
        )
        for rank, result in enumerate(results, start=1)
    ]


def explain_reranked(
    results: Sequence[RerankedResult],
    fused_results: Sequence[FusedResult],
) -> list[RetrievalExplanation]:
    """Explain reranked results against their original fused ordering.

    ``fused_results`` must be the ordered candidate sequence supplied to
    the reranker. This allows the explanation layer to report actual
    RRF-to-reranker movement without modifying the RerankedResult contract.
    """

    fused_ranks = {
        result.entry_id: rank
        for rank, result in enumerate(fused_results, start=1)
    }

    explanations: list[RetrievalExplanation] = []

    for reranker_rank, result in enumerate(results, start=1):
        if result.reranker_rank != reranker_rank:
            raise ValueError(
                "reranker_rank must match the supplied result sequence"
            )

        fused_rank = fused_ranks.get(result.entry_id)

        if fused_rank is None:
            raise ValueError(
                f"reranked entry {result.entry_id} is absent from fused results"
            )

        explanations.append(
            RetrievalExplanation(
                entry_id=result.entry_id,
                source_profile=result.source_profile,
                origin_memory_id=result.origin_memory_id,
                keyword_rank=result.keyword_rank,
                keyword_contribution=result.keyword_contribution,
                semantic_rank=result.semantic_rank,
                semantic_contribution=result.semantic_contribution,
                graph_rank=result.graph_rank,
                graph_contribution=result.graph_contribution,
                temporal_rank=result.temporal_rank,
                temporal_contribution=result.temporal_contribution,
                fused_score=result.fused_score,
                fused_rank=fused_rank,
                reranker_score=result.reranker_score,
                reranker_rank=reranker_rank,
                rank_change=fused_rank - reranker_rank,
                provenance=result.provenance,
            )
        )

    return explanations

"""Deterministic retrieval diagnostics for Phase 15F.

This module composes already-produced retrieval metadata and evaluation
signals into an inspectable diagnostic snapshot.

Diagnostics do not retrieve memory content, authorize candidates, mutate
governance state, persist results, or alter ranking behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.retrieval.retrieval_evaluation import (
    RetrievalEvaluation,
    evaluate_retrieval,
)
from src.retrieval.reranker import RerankDiagnostics


@dataclass(frozen=True)
class RetrievalResultDiagnostics:
    """Inspectability metadata for one ranked retrieval result."""

    entry_id: int
    rank: int
    source_profile: str
    origin_memory_id: str
    fused_rank: int
    reranker_rank: int | None
    rank_change: int | None
    keyword_rank: int | None
    semantic_rank: int | None
    graph_rank: int | None
    temporal_rank: int | None
    entity_rank: int | None
    evidence_present: bool
    provenance_present: bool


@dataclass(frozen=True)
class RetrievalDiagnostics:
    """Deterministic diagnostic snapshot for one retrieval operation."""

    query: str
    result_count: int
    requested_top_k: int
    candidate_limit: int
    result_entry_ids: tuple[int, ...]
    reranking_enabled: bool
    reranker_diagnostics: RerankDiagnostics | None
    result_diagnostics: tuple[RetrievalResultDiagnostics, ...]
    evaluation: RetrievalEvaluation | None


def _validate_positive_integer(name: str, value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{name} must be a positive integer")


def _validate_query(query: str) -> None:
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    if not query.strip():
        raise ValueError("query must be a non-empty string")


def build_retrieval_diagnostics(
    query: str,
    results: Sequence[object],
    *,
    requested_top_k: int,
    candidate_limit: int,
    reranking_enabled: bool,
    reranker_diagnostics: RerankDiagnostics | None = None,
    relevant_entry_ids: Sequence[int] | None = None,
    evaluation_k: int | None = None,
) -> RetrievalDiagnostics:
    """Build diagnostics from an already-produced ranked result sequence.

    Only result metadata is consumed. The diagnostic layer never accesses
    source memory content and never changes the supplied result ordering.
    """

    _validate_query(query)
    _validate_positive_integer("requested_top_k", requested_top_k)
    _validate_positive_integer("candidate_limit", candidate_limit)

    if evaluation_k is not None:
        _validate_positive_integer("evaluation_k", evaluation_k)

        if relevant_entry_ids is None:
            raise ValueError(
                "relevant_entry_ids must be supplied when evaluation_k is set"
            )

    result_list = tuple(results)

    result_entry_ids = tuple(
        int(result.entry_id)
        for result in result_list
    )

    result_diagnostics: list[RetrievalResultDiagnostics] = []

    for rank, result in enumerate(result_list, start=1):
        evidence_signal = getattr(result, "evidence_signal", None)
        provenance = getattr(result, "provenance", None)

        result_diagnostics.append(
            RetrievalResultDiagnostics(
                entry_id=int(result.entry_id),
                rank=rank,
                source_profile=str(result.source_profile),
                origin_memory_id=str(result.origin_memory_id),
                fused_rank=int(result.fused_rank),
                reranker_rank=(
                    int(result.reranker_rank)
                    if result.reranker_rank is not None
                    else None
                ),
                rank_change=(
                    int(result.rank_change)
                    if result.rank_change is not None
                    else None
                ),
                keyword_rank=(
                    int(result.keyword_rank)
                    if result.keyword_rank is not None
                    else None
                ),
                semantic_rank=(
                    int(result.semantic_rank)
                    if result.semantic_rank is not None
                    else None
                ),
                graph_rank=(
                    int(result.graph_rank)
                    if result.graph_rank is not None
                    else None
                ),
                temporal_rank=(
                    int(result.temporal_rank)
                    if result.temporal_rank is not None
                    else None
                ),
                entity_rank=(
                    int(result.entity_rank)
                    if result.entity_rank is not None
                    else None
                ),
                evidence_present=evidence_signal is not None,
                provenance_present=provenance is not None,
            )
        )

    evaluation = None

    if evaluation_k is not None:
        evaluation = evaluate_retrieval(
            result_list,
            relevant_entry_ids or (),
            k=evaluation_k,
        )

    return RetrievalDiagnostics(
        query=query,
        result_count=len(result_list),
        requested_top_k=requested_top_k,
        candidate_limit=candidate_limit,
        result_entry_ids=result_entry_ids,
        reranking_enabled=bool(reranking_enabled),
        reranker_diagnostics=reranker_diagnostics,
        result_diagnostics=tuple(result_diagnostics),
        evaluation=evaluation,
    )

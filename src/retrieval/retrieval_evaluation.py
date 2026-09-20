"""Deterministic retrieval-quality evaluation for Phase 15E-C.

The evaluator operates only on already-produced retrieval results. It does
not retrieve, authorize, mutate, persist, or expose memory content.

Metrics are descriptive evaluation signals and never participate in retrieval
governance or ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RetrievalEvaluation:
    """Quality metrics for one ranked retrieval result set."""

    retrieved_entry_ids: tuple[int, ...]
    relevant_entry_ids: tuple[int, ...]
    evaluated_k: int
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float


def _validate_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer")


def _normalize_relevant_ids(relevant_entry_ids: Sequence[int]) -> tuple[int, ...]:
    if isinstance(relevant_entry_ids, (str, bytes)):
        raise TypeError("relevant_entry_ids must be a sequence of entry IDs")

    normalized = tuple(int(entry_id) for entry_id in relevant_entry_ids)

    if len(set(normalized)) != len(normalized):
        raise ValueError("relevant_entry_ids must not contain duplicates")

    return normalized


def precision_at_k(
    retrieved_entry_ids: Sequence[int],
    relevant_entry_ids: Sequence[int],
    k: int,
) -> float:
    """Return precision among the first ``k`` ranked results."""

    _validate_k(k)
    relevant = set(_normalize_relevant_ids(relevant_entry_ids))

    retrieved = tuple(int(entry_id) for entry_id in retrieved_entry_ids[:k])

    if not retrieved:
        return 0.0

    relevant_retrieved = sum(
        entry_id in relevant
        for entry_id in retrieved
    )

    return relevant_retrieved / len(retrieved)


def recall_at_k(
    retrieved_entry_ids: Sequence[int],
    relevant_entry_ids: Sequence[int],
    k: int,
) -> float:
    """Return recall among the first ``k`` ranked results."""

    _validate_k(k)
    relevant = _normalize_relevant_ids(relevant_entry_ids)

    if not relevant:
        return 0.0

    retrieved = {
        int(entry_id)
        for entry_id in retrieved_entry_ids[:k]
    }

    return len(retrieved.intersection(relevant)) / len(relevant)


def mean_reciprocal_rank(
    retrieved_entry_ids: Sequence[int],
    relevant_entry_ids: Sequence[int],
) -> float:
    """Return reciprocal rank of the first relevant result.

    For a single ranked result list this is the usual reciprocal-rank
    calculation. The name is retained because it matches standard retrieval
    evaluation terminology.
    """

    relevant = set(_normalize_relevant_ids(relevant_entry_ids))

    if not relevant:
        return 0.0

    for rank, entry_id in enumerate(retrieved_entry_ids, start=1):
        if int(entry_id) in relevant:
            return 1.0 / rank

    return 0.0


def evaluate_retrieval(
    results: Sequence[object],
    relevant_entry_ids: Sequence[int],
    *,
    k: int,
) -> RetrievalEvaluation:
    """Evaluate an already-produced ranked retrieval result sequence.

    Only ``entry_id`` is consumed from result objects. Provenance and other
    governed metadata remain untouched because the evaluator does not create
    or transform retrieval results.
    """

    _validate_k(k)
    relevant = _normalize_relevant_ids(relevant_entry_ids)

    retrieved = tuple(
        int(result.entry_id)
        for result in results
    )

    evaluated_k = min(k, len(retrieved))

    return RetrievalEvaluation(
        retrieved_entry_ids=retrieved,
        relevant_entry_ids=relevant,
        evaluated_k=evaluated_k,
        precision_at_k=precision_at_k(
            retrieved,
            relevant,
            k,
        ),
        recall_at_k=recall_at_k(
            retrieved,
            relevant,
            k,
        ),
        mean_reciprocal_rank=mean_reciprocal_rank(
            retrieved,
            relevant,
        ),
    )

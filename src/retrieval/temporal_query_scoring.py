"""Deterministic scoring of governed temporal retrieval results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TemporalQueryScore:
    """Descriptive temporal relevance for one retrieved result."""

    score: float
    overlaps: bool
    within_query_window: bool
    date_source: str


def score_temporal_result(
    *,
    memory_date: datetime,
    query_start: datetime,
    query_end: datetime,
    date_source: str,
) -> TemporalQueryScore:
    """Score one governed temporal result against an explicit window.

    This does not modify the governed temporal retrieval score.
    """

    if query_start > query_end:
        raise ValueError(
            "query_start must not be after query_end"
        )

    overlaps = query_start <= memory_date <= query_end

    return TemporalQueryScore(
        score=1.0 if overlaps else 0.0,
        overlaps=overlaps,
        within_query_window=overlaps,
        date_source=date_source,
    )

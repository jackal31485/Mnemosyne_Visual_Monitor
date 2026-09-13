"""Evidence-preserving temporal context attached to hybrid results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.retrieval.temporal_query_scoring import TemporalQueryScore


@dataclass(frozen=True)
class TemporalResultContext:
    """Descriptive temporal context for a hybrid retrieval result."""

    temporal_score: float
    temporal_relevant: bool
    date_source: str
    query_start: datetime
    query_end: datetime


def build_temporal_result_context(
    *,
    query_start: datetime,
    query_end: datetime,
    temporal_score: TemporalQueryScore,
) -> TemporalResultContext:
    """Build immutable temporal query context."""

    if query_start > query_end:
        raise ValueError(
            "query_start must not be after query_end"
        )

    return TemporalResultContext(
        temporal_score=temporal_score.score,
        temporal_relevant=temporal_score.overlaps,
        date_source=temporal_score.date_source,
        query_start=query_start,
        query_end=query_end,
    )

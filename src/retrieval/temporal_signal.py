"""Evidence-preserving temporal signals for governed retrieval results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.retrieval.temporal_result_context import TemporalResultContext


@dataclass(frozen=True)
class TemporalSignal:
    """Inspectable temporal relevance without rewriting temporal meaning."""

    relevant: bool
    score: float
    date_source: str
    query_start: datetime | None
    query_end: datetime | None


def build_temporal_signal(
    context: TemporalResultContext | None,
) -> TemporalSignal:
    """Convert existing temporal context into an immutable retrieval signal."""

    if context is None:
        return TemporalSignal(
            relevant=False,
            score=0.0,
            date_source="unknown",
            query_start=None,
            query_end=None,
        )

    return TemporalSignal(
        relevant=context.temporal_relevant,
        score=context.temporal_score,
        date_source=context.date_source,
        query_start=context.query_start,
        query_end=context.query_end,
    )

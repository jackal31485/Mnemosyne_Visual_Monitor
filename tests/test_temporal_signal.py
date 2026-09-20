from datetime import datetime

from src.retrieval.temporal_query_scoring import TemporalQueryScore
from src.retrieval.temporal_result_context import (
    build_temporal_result_context,
)
from src.retrieval.temporal_signal import build_temporal_signal


def test_missing_context_is_non_relevant():
    signal = build_temporal_signal(None)

    assert signal.relevant is False
    assert signal.score == 0.0
    assert signal.date_source == "unknown"
    assert signal.query_start is None
    assert signal.query_end is None


def test_context_is_preserved_without_rewriting():
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 31)

    score = TemporalQueryScore(
        score=1.0,
        overlaps=True,
        within_query_window=True,
        date_source="event_date",
    )

    context = build_temporal_result_context(
        query_start=start,
        query_end=end,
        temporal_score=score,
    )

    signal = build_temporal_signal(context)

    assert signal.relevant is True
    assert signal.score == 1.0
    assert signal.date_source == "event_date"
    assert signal.query_start == start
    assert signal.query_end == end

from datetime import datetime

import pytest

from src.retrieval.temporal_query_scoring import TemporalQueryScore
from src.retrieval.temporal_result_context import (
    build_temporal_result_context,
)


def test_context_preserves_temporal_score_and_window():
    start = datetime(2026, 9, 1)
    end = datetime(2026, 9, 10, 23, 59, 59)

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

    assert context.temporal_score == 1.0
    assert context.temporal_relevant is True
    assert context.date_source == "event_date"
    assert context.query_start == start
    assert context.query_end == end


def test_context_rejects_reversed_window():
    with pytest.raises(ValueError):
        build_temporal_result_context(
            query_start=datetime(2026, 9, 10),
            query_end=datetime(2026, 9, 1),
            temporal_score=TemporalQueryScore(
                score=0.0,
                overlaps=False,
                within_query_window=False,
                date_source="event_date",
            ),
        )

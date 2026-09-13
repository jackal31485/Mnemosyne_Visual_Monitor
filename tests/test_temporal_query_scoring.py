from datetime import datetime

import pytest

from src.retrieval.temporal_query_scoring import (
    score_temporal_result,
)


def test_result_inside_window_is_relevant():
    result = score_temporal_result(
        memory_date=datetime(2026, 9, 5, 12, 0),
        query_start=datetime(2026, 9, 1),
        query_end=datetime(2026, 9, 10, 23, 59, 59),
        date_source="event_date",
    )

    assert result.score == 1.0
    assert result.overlaps is True
    assert result.within_query_window is True
    assert result.date_source == "event_date"


def test_result_outside_window_is_not_relevant():
    result = score_temporal_result(
        memory_date=datetime(2026, 9, 15),
        query_start=datetime(2026, 9, 1),
        query_end=datetime(2026, 9, 10, 23, 59, 59),
        date_source="event_date",
    )

    assert result.score == 0.0
    assert result.overlaps is False
    assert result.within_query_window is False


def test_window_boundaries_are_inclusive():
    start = datetime(2026, 9, 1)
    end = datetime(2026, 9, 10, 23, 59, 59)

    assert score_temporal_result(
        memory_date=start,
        query_start=start,
        query_end=end,
        date_source="event_date",
    ).score == 1.0

    assert score_temporal_result(
        memory_date=end,
        query_start=start,
        query_end=end,
        date_source="event_date",
    ).score == 1.0


def test_reversed_window_is_rejected():
    with pytest.raises(ValueError):
        score_temporal_result(
            memory_date=datetime(2026, 9, 5),
            query_start=datetime(2026, 9, 10),
            query_end=datetime(2026, 9, 1),
            date_source="event_date",
        )

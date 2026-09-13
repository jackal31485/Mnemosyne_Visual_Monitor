from datetime import date, datetime, time

import pytest

from src.retrieval.temporal_query import (
    TemporalQueryIntent,
    build_event_date_intent,
)


def test_empty_intent_has_no_constraint():
    intent = build_event_date_intent(None, None)

    assert intent.has_constraint is False
    assert intent.is_complete_window is False
    assert intent.start is None
    assert intent.end is None


def test_event_date_intent_preserves_explicit_window():
    intent = build_event_date_intent(
        date(2026, 9, 1),
        date(2026, 9, 7),
    )

    assert intent.has_constraint is True
    assert intent.is_complete_window is True
    assert intent.start == datetime.combine(
        date(2026, 9, 1),
        time.min,
    )
    assert intent.end == datetime.combine(
        date(2026, 9, 7),
        time.max,
    )


def test_partial_window_is_rejected():
    with pytest.raises(ValueError):
        build_event_date_intent(
            date(2026, 9, 1),
            None,
        )


def test_reversed_window_is_rejected():
    intent = TemporalQueryIntent(
        start=datetime(2026, 9, 7),
        end=datetime(2026, 9, 1),
    )

    with pytest.raises(ValueError):
        intent.validate()


def test_missing_temporal_values_are_not_inferred():
    intent = TemporalQueryIntent()

    assert intent.start is None
    assert intent.end is None

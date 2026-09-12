from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domain.temporal_precision import (
    PrecisionInterval,
    compare_precision_intervals,
    evidence_to_precision_interval,
)


def evidence(
    evidence_id: int,
    start: str | None,
    end: str | None = None,
    precision: str = "day",
):
    return SimpleNamespace(
        temporal_evidence_id=evidence_id,
        start_time=start,
        end_time=end,
        precision=precision,
    )


def test_year_precision_expands_to_full_year():
    result = evidence_to_precision_interval(
        evidence(1, "2024", precision="year")
    )

    assert result is not None
    assert result.start.isoformat() == "2024-01-01T00:00:00"
    assert result.end.isoformat() == "2024-12-31T23:59:59.999999"


def test_month_precision_expands_to_full_month():
    result = evidence_to_precision_interval(
        evidence(1, "2024-02", precision="month")
    )

    assert result is not None
    assert result.start.isoformat() == "2024-02-01T00:00:00"
    assert result.end.isoformat() == "2024-02-29T23:59:59.999999"


def test_day_precision_expands_to_day_boundary():
    result = evidence_to_precision_interval(
        evidence(1, "2024-02-29", precision="day")
    )

    assert result is not None
    assert result.start.isoformat() == "2024-02-29T00:00:00"
    assert result.end.isoformat() == "2024-02-29T23:59:59.999999"


def test_hour_precision_expands_to_hour_boundary():
    result = evidence_to_precision_interval(
        evidence(
            1,
            "2024-02-29T14:00:00",
            precision="hour",
        )
    )

    assert result is not None
    assert result.end.isoformat() == "2024-02-29T14:59:59.999999"


def test_minute_precision_expands_to_minute_boundary():
    result = evidence(
        1,
        "2024-02-29T14:30:00",
        precision="minute",
    )

    interval = evidence_to_precision_interval(result)

    assert interval is not None
    assert interval.end.isoformat() == "2024-02-29T14:30:59.999999"


def test_second_precision_remains_exact():
    result = evidence_to_precision_interval(
        evidence(
            1,
            "2024-02-29T14:30:45",
            precision="second",
        )
    )

    assert result is not None
    assert result.start.isoformat() == "2024-02-29T14:30:45"
    assert result.end.isoformat() == "2024-02-29T14:30:45"


def test_unknown_precision_is_indeterminate():
    assert (
        evidence_to_precision_interval(
            evidence(1, "2024", precision="unknown")
        )
        is None
    )


def test_missing_start_is_indeterminate():
    assert evidence_to_precision_interval(
        evidence(1, None, precision="day")
    ) is None


def test_year_does_not_become_exact_january_event():
    result = evidence_to_precision_interval(
        evidence(1, "2024", precision="year")
    )

    assert result is not None
    assert result.start.month == 1
    assert result.start.day == 1
    assert result.end.month == 12
    assert result.end.day == 31


def test_year_precision_can_be_definitely_before_another_year():
    left = evidence_to_precision_interval(
        evidence(1, "2024", precision="year")
    )
    right = evidence_to_precision_interval(
        evidence(2, "2025", precision="year")
    )

    assert left is not None
    assert right is not None

    result = compare_precision_intervals(left, right)

    assert result.relation == "before"
    assert result.certainty == "definite"


def test_same_year_is_exactly_same_semantic_interval():
    left = evidence_to_precision_interval(
        evidence(1, "2024", precision="year")
    )
    right = evidence_to_precision_interval(
        evidence(2, "2024", precision="year")
    )

    assert left is not None
    assert right is not None

    result = compare_precision_intervals(left, right)

    assert result.relation == "at"
    assert result.certainty == "definite"


def test_year_and_month_overlap_is_not_called_definite_order():
    year = evidence_to_precision_interval(
        evidence(1, "2024", precision="year")
    )
    month = evidence_to_precision_interval(
        evidence(2, "2024-06", precision="month")
    )

    assert year is not None
    assert month is not None

    result = compare_precision_intervals(year, month)

    assert result.relation == "contains"
    assert result.certainty == "definite"


def test_partial_precision_overlap_is_indeterminate():
    left = PrecisionInterval(
        evidence_id=1,
        start=__import__("datetime").datetime(2024, 1, 1),
        end=__import__("datetime").datetime(2024, 6, 30, 23, 59, 59),
        precision="month",
    )
    right = PrecisionInterval(
        evidence_id=2,
        start=__import__("datetime").datetime(2024, 6, 15),
        end=__import__("datetime").datetime(2024, 12, 31, 23, 59, 59),
        precision="month",
    )

    result = compare_precision_intervals(left, right)

    assert result.relation == "overlaps"
    assert result.certainty == "indeterminate"


def test_explicit_range_preserves_precision():
    result = evidence_to_precision_interval(
        evidence(
            1,
            "2024",
            "2025",
            precision="year",
        )
    )

    assert result is not None
    assert result.start.year == 2024
    assert result.end.year == 2025
    assert result.end.month == 12
    assert result.end.day == 31


def test_invalid_precision_is_rejected():
    with pytest.raises(ValueError):
        evidence_to_precision_interval(
            evidence(1, "2024", precision="quarter")
        )


def test_invalid_precision_interval_order_is_rejected():
    from datetime import datetime

    with pytest.raises(ValueError):
        PrecisionInterval(
            evidence_id=1,
            start=datetime(2025, 1, 1),
            end=datetime(2024, 1, 1),
            precision="year",
        )

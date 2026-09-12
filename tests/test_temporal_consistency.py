from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.temporal_consistency import (
    TemporalConflict,
    TemporalConsistencyReport,
    analyze_temporal_consistency,
    compare_subject_timelines,
    detect_temporal_conflicts,
)
from src.domain.temporal_precision import (
    PrecisionInterval,
)


def interval(
    evidence_id: int,
    start: datetime,
    end: datetime,
    precision: str = "day",
) -> PrecisionInterval:
    return PrecisionInterval(
        evidence_id=evidence_id,
        start=start,
        end=end,
        precision=precision,
    )


def test_compare_subject_timelines_compares_each_pair():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 2, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 3),
            datetime(2024, 1, 4, 23, 59, 59),
        ),
        interval(
            3,
            datetime(2024, 1, 5),
            datetime(2024, 1, 6, 23, 59, 59),
        ),
    )

    results = compare_subject_timelines(values)

    assert len(results) == 3
    assert results[0].subject_evidence_id == 1
    assert results[0].object_evidence_id == 2
    assert results[1].subject_evidence_id == 1
    assert results[1].object_evidence_id == 3
    assert results[2].subject_evidence_id == 2
    assert results[2].object_evidence_id == 3


def test_comparison_order_is_deterministic():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 2),
            datetime(2024, 1, 2, 23, 59, 59),
        ),
    )

    first = compare_subject_timelines(values)
    second = compare_subject_timelines(values)

    assert first == second


def test_definite_before_is_not_a_conflict():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 2),
            datetime(2024, 1, 2, 23, 59, 59),
        ),
    )

    assert detect_temporal_conflicts(values) == ()


def test_definite_after_is_not_a_conflict():
    values = (
        interval(
            1,
            datetime(2024, 1, 2),
            datetime(2024, 1, 2, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
        ),
    )

    assert detect_temporal_conflicts(values) == ()


def test_overlapping_precision_is_not_called_a_conflict():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 5),
            datetime(2024, 1, 15, 23, 59, 59),
        ),
    )

    results = compare_subject_timelines(values)

    assert results[0].relation == "overlaps"
    assert results[0].certainty == "indeterminate"
    assert detect_temporal_conflicts(values) == ()


def test_nested_intervals_are_not_conflicts():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 10),
            datetime(2024, 1, 20, 23, 59, 59),
        ),
    )

    results = compare_subject_timelines(values)

    assert results[0].relation == "contains"
    assert results[0].certainty == "definite"
    assert detect_temporal_conflicts(values) == ()


def test_equal_intervals_are_not_conflicts():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
        ),
    )

    results = compare_subject_timelines(values)

    assert results[0].relation == "at"
    assert results[0].certainty == "definite"
    assert detect_temporal_conflicts(values) == ()


def test_report_contains_comparisons_and_conflicts():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
        ),
        interval(
            2,
            datetime(2024, 1, 2),
            datetime(2024, 1, 2, 23, 59, 59),
        ),
    )

    report = analyze_temporal_consistency(values)

    assert isinstance(report, TemporalConsistencyReport)
    assert report.comparison_count == 1
    assert report.conflict_count == 0


def test_empty_input_returns_empty_report():
    report = analyze_temporal_consistency(())

    assert report.comparisons == ()
    assert report.conflicts == ()
    assert report.comparison_count == 0
    assert report.conflict_count == 0


def test_single_interval_returns_no_comparisons():
    value = interval(
        1,
        datetime(2024, 1, 1),
        datetime(2024, 1, 1, 23, 59, 59),
    )

    report = analyze_temporal_consistency((value,))

    assert report.comparisons == ()
    assert report.conflicts == ()


def test_invalid_input_is_rejected():
    with pytest.raises(TypeError):
        compare_subject_timelines([object()])


def test_conflict_requires_distinct_evidence_ids():
    with pytest.raises(ValueError):
        TemporalConflict(
            subject_evidence_id=1,
            object_evidence_id=1,
            reason="invalid",
        )


def test_empty_conflict_reason_is_rejected():
    with pytest.raises(ValueError):
        TemporalConflict(
            subject_evidence_id=1,
            object_evidence_id=2,
            reason="",
        )


def test_precision_uncertainty_does_not_create_false_conflict():
    values = (
        interval(
            1,
            datetime(2024, 1, 1),
            datetime(2024, 1, 31, 23, 59, 59),
            precision="month",
        ),
        interval(
            2,
            datetime(2024, 1, 15),
            datetime(2024, 1, 15, 23, 59, 59),
            precision="day",
        ),
    )

    report = analyze_temporal_consistency(values)

    assert report.conflicts == ()
    assert report.comparisons[0].relation == "contains"

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domain.temporal_reasoning import (
    TemporalInterval,
    TemporalRelationship,
    compare_intervals,
    evidence_to_interval,
    reason_over_evidence,
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


def interval(
    evidence_id: int,
    start: str,
    end: str,
) -> TemporalInterval:
    from datetime import datetime

    return TemporalInterval(
        evidence_id=evidence_id,
        start_time=datetime.fromisoformat(start),
        end_time=datetime.fromisoformat(end),
    )


def test_bounded_evidence_becomes_interval():
    result = evidence_to_interval(
        evidence(
            1,
            "2026-09-10T00:00:00",
            "2026-09-12T00:00:00",
        )
    )

    assert result is not None
    assert result.evidence_id == 1
    assert result.start_time.isoformat() == "2026-09-10T00:00:00"
    assert result.end_time.isoformat() == "2026-09-12T00:00:00"


def test_point_evidence_becomes_zero_length_interval():
    result = evidence_to_interval(
        evidence(1, "2026-09-10T00:00:00")
    )

    assert result is not None
    assert result.start_time == result.end_time


def test_unknown_precision_is_not_reasoned_over():
    assert (
        evidence_to_interval(
            evidence(
                1,
                "2026-09-10T00:00:00",
                precision="unknown",
            )
        )
        is None
    )


def test_missing_start_is_not_reasoned_over():
    assert evidence_to_interval(evidence(1, None)) is None


@pytest.mark.parametrize(
    ("left_start", "left_end", "right_start", "right_end", "expected"),
    [
        (
            "2026-09-09T00:00:00",
            "2026-09-10T00:00:00",
            "2026-09-11T00:00:00",
            "2026-09-12T00:00:00",
            "before",
        ),
        (
            "2026-09-11T00:00:00",
            "2026-09-12T00:00:00",
            "2026-09-09T00:00:00",
            "2026-09-10T00:00:00",
            "after",
        ),
        (
            "2026-09-09T00:00:00",
            "2026-09-10T00:00:00",
            "2026-09-10T00:00:00",
            "2026-09-11T00:00:00",
            "meets",
        ),
    ],
)
def test_order_relationships(
    left_start,
    left_end,
    right_start,
    right_end,
    expected,
):
    left = interval(
        1,
        left_start,
        left_end,
    )
    right = interval(
        2,
        right_start,
        right_end,
    )

    result = compare_intervals(left, right)

    assert result.relation == expected


def test_overlapping_intervals():
    left = interval(
        1,
        "2026-09-10T00:00:00",
        "2026-09-12T00:00:00",
    )
    right = interval(
        2,
        "2026-09-11T00:00:00",
        "2026-09-13T00:00:00",
    )

    assert compare_intervals(left, right).relation == "overlaps"


def test_during_relationship():
    outer = interval(
        1,
        "2026-09-10T00:00:00",
        "2026-09-20T00:00:00",
    )
    inner = interval(
        2,
        "2026-09-12T00:00:00",
        "2026-09-15T00:00:00",
    )

    assert compare_intervals(inner, outer).relation == "during"
    assert compare_intervals(outer, inner).relation == "contains"


def test_equal_intervals():
    left = interval(
        1,
        "2026-09-10T00:00:00",
        "2026-09-12T00:00:00",
    )
    right = interval(
        2,
        "2026-09-10T00:00:00",
        "2026-09-12T00:00:00",
    )

    assert compare_intervals(left, right).relation == "at"


def test_reasoning_preserves_pair_order():
    result = reason_over_evidence(
        [
            evidence(1, "2026-09-10T00:00:00"),
            evidence(2, "2026-09-12T00:00:00"),
            evidence(3, None),
        ]
    )

    assert len(result) == 1
    assert result[0].subject_evidence_id == 1
    assert result[0].object_evidence_id == 2
    assert result[0].relation == "before"


def test_invalid_interval_is_rejected():
    from datetime import datetime

    with pytest.raises(ValueError):
        TemporalInterval(
            evidence_id=1,
            start_time=datetime(2026, 9, 12),
            end_time=datetime(2026, 9, 10),
        )


def test_relationship_cannot_reference_itself():
    with pytest.raises(ValueError):
        TemporalRelationship(
            subject_evidence_id=1,
            object_evidence_id=1,
            relation="before",
        )

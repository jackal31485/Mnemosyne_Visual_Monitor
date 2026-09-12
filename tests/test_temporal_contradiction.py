from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.temporal_contradiction import (
    TemporalContradiction,
    TemporalStateAssertion,
    detect_state_contradictions,
)
from src.domain.temporal_precision import PrecisionInterval


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


def assertion(
    evidence_id: int,
    subject_id: str,
    state: str,
    start: datetime,
    end: datetime,
    precision: str = "day",
) -> TemporalStateAssertion:
    return TemporalStateAssertion(
        evidence_id=evidence_id,
        subject_type="entity",
        subject_id=subject_id,
        state=state,
        interval=interval(
            evidence_id,
            start,
            end,
            precision,
        ),
    )


def test_conflicting_states_for_same_subject_and_same_day_are_detected():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    result = detect_state_contradictions(values)

    assert len(result) == 1
    assert result[0].subject_id == "entity-1"
    assert result[0].left_state == "active"
    assert result[0].right_state == "inactive"
    assert result[0].relation == "at"


def test_different_subjects_are_not_contradictions():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-2",
            "inactive",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    assert detect_state_contradictions(values) == ()


def test_same_state_is_not_a_contradiction():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    assert detect_state_contradictions(values) == ()


def test_non_overlapping_states_are_not_contradictions():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 11),
            datetime(2024, 1, 11, 23, 59, 59),
        ),
    )

    assert detect_state_contradictions(values) == ()


def test_nested_conflicting_state_is_detected():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 31, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 10),
            datetime(2024, 1, 20, 23, 59, 59),
        ),
    )

    result = detect_state_contradictions(values)

    assert len(result) == 1
    assert result[0].relation == "contains"


def test_indeterminate_overlap_is_not_promoted_to_contradiction():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 10, 23, 59, 59),
            precision="day",
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 5),
            datetime(2024, 1, 15, 23, 59, 59),
            precision="day",
        ),
    )

    # The supplied envelopes overlap, but the precise event relationship
    # is not known. This must not be treated as a definite contradiction.
    #
    # With interval-level semantic boundaries this relationship is
    # represented as an indeterminate overlap.
    from src.domain.temporal_precision import compare_precision_intervals

    comparison = compare_precision_intervals(
        values[0].interval,
        values[1].interval,
    )

    assert comparison.relation == "overlaps"
    assert comparison.certainty == "indeterminate"
    assert detect_state_contradictions(values) == ()


def test_sequential_state_change_is_not_contradiction():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 11),
            datetime(2024, 1, 20, 23, 59, 59),
        ),
    )

    assert detect_state_contradictions(values) == ()


def test_multiple_contradictions_are_deterministic():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 5),
            datetime(2024, 1, 7, 23, 59, 59),
        ),
        assertion(
            3,
            "entity-1",
            "maintenance",
            datetime(2024, 1, 6),
            datetime(2024, 1, 8, 23, 59, 59),
        ),
    )

    first = detect_state_contradictions(values)
    second = detect_state_contradictions(values)

    assert first == second
    assert len(first) == 2
    assert first[0].left_evidence_id == 1
    assert first[0].right_evidence_id == 2
    assert first[1].left_evidence_id == 1
    assert first[1].right_evidence_id == 3


def test_empty_input_returns_no_contradictions():
    assert detect_state_contradictions(()) == ()


def test_invalid_input_is_rejected():
    with pytest.raises(TypeError):
        detect_state_contradictions([object()])


def test_interval_evidence_id_must_match_assertion():
    with pytest.raises(ValueError):
        TemporalStateAssertion(
            evidence_id=1,
            subject_type="entity",
            subject_id="entity-1",
            state="active",
            interval=interval(
                2,
                datetime(2024, 1, 1),
                datetime(2024, 1, 1, 23, 59, 59),
            ),
        )


def test_contradiction_requires_distinct_evidence_ids():
    with pytest.raises(ValueError):
        TemporalContradiction(
            subject_type="entity",
            subject_id="entity-1",
            left_evidence_id=1,
            right_evidence_id=1,
            left_state="active",
            right_state="inactive",
            relation="at",
            reason="invalid",
        )


def test_contradiction_cannot_use_identical_states():
    with pytest.raises(ValueError):
        TemporalContradiction(
            subject_type="entity",
            subject_id="entity-1",
            left_evidence_id=1,
            right_evidence_id=2,
            left_state="active",
            right_state="active",
            relation="at",
            reason="invalid",
        )


def test_conflicting_states_for_different_profiles_can_still_be_compared():
    left = TemporalStateAssertion(
        evidence_id=1,
        subject_type="entity",
        subject_id="entity-1",
        state="active",
        interval=interval(
            1,
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    right = TemporalStateAssertion(
        evidence_id=2,
        subject_type="entity",
        subject_id="entity-1",
        state="inactive",
        interval=interval(
            2,
            datetime(2024, 1, 10),
            datetime(2024, 1, 10, 23, 59, 59),
        ),
    )

    result = detect_state_contradictions((left, right))

    assert len(result) == 1
    assert result[0].subject_id == "entity-1"

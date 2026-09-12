from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.temporal_aggregation import (
    TemporalEvidenceGroup,
    TemporalStateGroup,
    aggregate_temporal_evidence,
    group_by_state,
    group_by_subject,
)
from src.domain.temporal_contradiction import TemporalStateAssertion
from src.domain.temporal_precision import PrecisionInterval


def assertion(
    evidence_id: int,
    subject_id: str,
    state: str,
    start: datetime,
    end: datetime,
    subject_type: str = "entity",
) -> TemporalStateAssertion:
    return TemporalStateAssertion(
        evidence_id=evidence_id,
        subject_type=subject_type,
        subject_id=subject_id,
        state=state,
        interval=PrecisionInterval(
            evidence_id=evidence_id,
            start=start,
            end=end,
            precision="day",
        ),
    )


def test_group_by_subject_combines_same_subject():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
    )

    result = group_by_subject(values)

    assert len(result) == 1
    assert result[0].subject_id == "entity-1"
    assert result[0].evidence_ids == (1, 2)


def test_group_by_subject_separates_subjects():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-2",
            "inactive",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
    )

    result = group_by_subject(values)

    assert len(result) == 2
    assert [group.subject_id for group in result] == [
        "entity-1",
        "entity-2",
    ]


def test_group_by_subject_preserves_all_evidence():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
        assertion(
            3,
            "entity-1",
            "maintenance",
            datetime(2024, 1, 5),
            datetime(2024, 1, 6),
        ),
    )

    result = group_by_subject(values)

    assert result[0].evidence_ids == (1, 2, 3)


def test_group_by_subject_orders_by_temporal_start():
    values = (
        assertion(
            3,
            "entity-1",
            "maintenance",
            datetime(2024, 1, 5),
            datetime(2024, 1, 6),
        ),
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
    )

    result = group_by_subject(values)

    assert result[0].evidence_ids == (1, 2, 3)


def test_equal_temporal_positions_use_evidence_id_as_tiebreaker():
    values = (
        assertion(
            3,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
        ),
        assertion(
            1,
            "entity-1",
            "inactive",
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
        ),
        assertion(
            2,
            "entity-1",
            "maintenance",
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
        ),
    )

    result = group_by_subject(values)

    assert result[0].evidence_ids == (1, 2, 3)


def test_group_states_are_sorted():
    values = (
        assertion(
            1,
            "entity-1",
            "inactive",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-1",
            "active",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
        assertion(
            3,
            "entity-1",
            "maintenance",
            datetime(2024, 1, 5),
            datetime(2024, 1, 6),
        ),
    )

    result = group_by_subject(values)

    assert result[0].states == (
        "active",
        "inactive",
        "maintenance",
    )


def test_group_by_state_separates_distinct_states():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-1",
            "inactive",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
        assertion(
            3,
            "entity-1",
            "active",
            datetime(2024, 1, 5),
            datetime(2024, 1, 6),
        ),
    )

    result = group_by_state(values)

    assert len(result) == 2
    assert result[0].state == "active"
    assert result[0].evidence_ids == (1, 3)
    assert result[1].state == "inactive"
    assert result[1].evidence_ids == (2,)


def test_group_by_state_preserves_subject_boundaries():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-2",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
    )

    result = group_by_state(values)

    assert len(result) == 2
    assert {
        (group.subject_id, group.state)
        for group in result
    } == {
        ("entity-1", "active"),
        ("entity-2", "active"),
    }


def test_aggregate_is_alias_for_subject_grouping_semantics():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            2,
            "entity-2",
            "active",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
    )

    assert aggregate_temporal_evidence(values) == group_by_subject(values)


def test_empty_input_returns_empty_groups():
    assert group_by_subject(()) == ()
    assert group_by_state(()) == ()
    assert aggregate_temporal_evidence(()) == ()


def test_invalid_input_is_rejected():
    with pytest.raises(TypeError):
        group_by_subject([object()])


def test_group_requires_matching_subject():
    value = assertion(
        1,
        "entity-1",
        "active",
        datetime(2024, 1, 1),
        datetime(2024, 1, 2),
    )

    with pytest.raises(ValueError):
        TemporalEvidenceGroup(
            subject_type="entity",
            subject_id="entity-2",
            assertions=(value,),
        )


def test_state_group_requires_matching_state():
    value = assertion(
        1,
        "entity-1",
        "active",
        datetime(2024, 1, 1),
        datetime(2024, 1, 2),
    )

    with pytest.raises(ValueError):
        TemporalStateGroup(
            subject_type="entity",
            subject_id="entity-1",
            state="inactive",
            assertions=(value,),
        )


def test_group_state_evidence_ids_are_deterministic():
    values = (
        assertion(
            5,
            "entity-1",
            "active",
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
        ),
        assertion(
            2,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
        ),
        assertion(
            4,
            "entity-1",
            "active",
            datetime(2024, 1, 2),
            datetime(2024, 1, 2),
        ),
    )

    result = group_by_state(values)

    assert result[0].evidence_ids == (2, 4, 5)


def test_multiple_subject_types_remain_separate():
    values = (
        assertion(
            1,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            subject_type="entity",
        ),
        assertion(
            2,
            "entity-1",
            "active",
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            subject_type="relationship",
        ),
    )

    result = group_by_subject(values)

    assert len(result) == 2
    assert {
        group.subject_type
        for group in result
    } == {"entity", "relationship"}

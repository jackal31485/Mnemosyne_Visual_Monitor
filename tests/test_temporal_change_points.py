from __future__ import annotations

import pytest

from src.domain.temporal_change_points import (
    TemporalChangePoint,
    TemporalChangePointAnalysis,
    TemporalStableRun,
    analyze_change_point_groups,
    analyze_change_points,
)
from src.domain.temporal_trajectory import (
    TemporalTrajectory,
    TemporalTrajectoryKind,
)


def trajectory(observation_count: int) -> TemporalTrajectory:
    return TemporalTrajectory(
        subject_type="person",
        subject_id="subject-1",
        kind=TemporalTrajectoryKind.TRANSITION,
        observation_count=observation_count,
        distinct_state_count=2,
        transition_count=2 if observation_count >= 3 else 0,
        reversal_count=0,
        oscillation_count=0,
        history_count=1,
        has_divergence=False,
        has_incomplete_history=False,
        has_temporal_uncertainty=False,
    )


def test_change_point_validates_values():
    with pytest.raises(ValueError):
        TemporalChangePoint(0, "a", "b")

    with pytest.raises(ValueError):
        TemporalChangePoint(1, "", "b")

    with pytest.raises(ValueError):
        TemporalChangePoint(1, "a", "")


def test_change_point_transition():
    point = TemporalChangePoint(2, "active", "inactive")

    assert point.transition == ("active", "inactive")


def test_stable_run_validates_values():
    with pytest.raises(ValueError):
        TemporalStableRun(-1, 1, "active")

    with pytest.raises(ValueError):
        TemporalStableRun(2, 1, "active")

    with pytest.raises(ValueError):
        TemporalStableRun(0, 1, "")


def test_stable_run_observation_count():
    run = TemporalStableRun(2, 4, "active")

    assert run.observation_count == 3


def test_stable_trajectory_has_no_change_points():
    result = analyze_change_points(
        trajectory(3),
        ["active", "active", "active"],
    )

    assert isinstance(result, TemporalChangePointAnalysis)
    assert result.change_point_count == 0
    assert result.stable_run_count == 1
    assert result.longest_stable_run == 3
    assert not result.has_change_points
    assert result.has_stable_runs


def test_single_transition_has_one_change_point():
    result = analyze_change_points(
        trajectory(2),
        ["active", "inactive"],
    )

    assert result.change_point_count == 1
    assert result.change_points[0].index == 1
    assert result.change_points[0].previous_state == "active"
    assert result.change_points[0].next_state == "inactive"


def test_multiple_changes_produce_ordered_change_points():
    result = analyze_change_points(
        trajectory(5),
        ["active", "inactive", "inactive", "active", "active"],
    )

    assert [
        (point.index, point.transition)
        for point in result.change_points
    ] == [
        (1, ("active", "inactive")),
        (3, ("inactive", "active")),
    ]


def test_stable_runs_surround_change_points():
    result = analyze_change_points(
        trajectory(6),
        [
            "active",
            "active",
            "inactive",
            "inactive",
            "active",
            "active",
        ],
    )

    assert [
        (
            run.start_index,
            run.end_index,
            run.state,
            run.observation_count,
        )
        for run in result.stable_runs
    ] == [
        (0, 1, "active", 2),
        (2, 3, "inactive", 2),
        (4, 5, "active", 2),
    ]

    assert result.longest_stable_run == 2


def test_unchanged_observation_does_not_create_change_point():
    result = analyze_change_points(
        trajectory(4),
        ["active", "inactive", "active", "active"],
    )

    assert result.observation_count == 4
    assert result.change_point_count == 2
    assert [
        point.index for point in result.change_points
    ] == [1, 2]
    assert result.longest_stable_run == 2


def test_reversal_has_two_change_points():
    result = analyze_change_points(
        trajectory(3),
        ["active", "inactive", "active"],
    )

    assert result.change_point_count == 2
    assert [
        point.transition for point in result.change_points
    ] == [
        ("active", "inactive"),
        ("inactive", "active"),
    ]


def test_empty_sequence_is_supported():
    empty = TemporalTrajectory(
        subject_type="person",
        subject_id="subject-1",
        kind=TemporalTrajectoryKind.EMPTY,
        observation_count=0,
        distinct_state_count=0,
        transition_count=0,
        reversal_count=0,
        oscillation_count=0,
        history_count=1,
        has_divergence=False,
        has_incomplete_history=False,
        has_temporal_uncertainty=False,
    )

    result = analyze_change_points(empty, [])

    assert result.observation_count == 0
    assert result.change_point_count == 0
    assert result.stable_run_count == 0
    assert result.longest_stable_run == 0


def test_mismatched_state_count_is_rejected():
    with pytest.raises(ValueError):
        analyze_change_points(
            trajectory(3),
            ["active", "inactive"],
        )


def test_empty_state_is_rejected():
    with pytest.raises(ValueError):
        analyze_change_points(
            trajectory(2),
            ["active", ""],
        )


def test_invalid_trajectory_type_is_rejected():
    with pytest.raises(TypeError):
        analyze_change_points(object(), [])  # type: ignore[arg-type]


def test_groups_are_deterministic():
    first = trajectory(2)

    second = TemporalTrajectory(
        subject_type="person",
        subject_id="subject-2",
        kind=TemporalTrajectoryKind.STABLE,
        observation_count=2,
        distinct_state_count=1,
        transition_count=0,
        reversal_count=0,
        oscillation_count=0,
        history_count=1,
        has_divergence=False,
        has_incomplete_history=False,
        has_temporal_uncertainty=False,
    )

    result = analyze_change_point_groups(
        {
            ("person", "subject-2"): (second, ["active", "active"]),
            ("person", "subject-1"): (first, ["active", "inactive"]),
        }
    )

    assert list(result) == [
        ("person", "subject-1"),
        ("person", "subject-2"),
    ]

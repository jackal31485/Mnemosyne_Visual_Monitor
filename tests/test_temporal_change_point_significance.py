from __future__ import annotations

from src.domain.temporal_change_point_significance import (
    analyze_change_point_significance,
)
from src.domain.temporal_change_points import analyze_change_points
from src.domain.temporal_trajectory import TemporalTrajectory, TemporalTrajectoryKind


def trajectory(count: int) -> TemporalTrajectory:
    return TemporalTrajectory(
        subject_type="person", subject_id="subject-1", kind=TemporalTrajectoryKind.TRANSITION,
        observation_count=count, distinct_state_count=2, transition_count=2,
        reversal_count=1, oscillation_count=0, history_count=1,
        has_divergence=False, has_incomplete_history=False, has_temporal_uncertainty=False,
    )


def test_change_point_significance_uses_adjacent_runs():
    analysis = analyze_change_points(
        trajectory(6), ["active", "active", "inactive", "inactive", "active", "active"]
    )
    result = analyze_change_point_significance(analysis)
    assert result.change_point_count == 2
    assert [point.persistence_score for point in result.change_points] == [2, 2]
    assert result.persistent_change_point_count == 2


def test_single_observation_runs_are_not_persistent():
    analysis = analyze_change_points(trajectory(3), ["active", "inactive", "active"])
    result = analyze_change_point_significance(analysis)
    assert result.persistent_change_point_count == 0
    assert not any(point.is_persistent for point in result.change_points)

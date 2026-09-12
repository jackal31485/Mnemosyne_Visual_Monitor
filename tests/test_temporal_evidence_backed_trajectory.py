from __future__ import annotations

from src.domain.temporal_evidence_backed_trajectory import analyze_evidence_backed_trajectory
from src.domain.temporal_state_history import TemporalStateHistory
from src.domain.temporal_trajectory import TemporalTrajectory, TemporalTrajectoryKind


def test_evidence_backed_trajectory_retains_evidence_ids():
    history = TemporalStateHistory(
        subject_type="person", subject_id="subject-1",
        evidence_ids=(1, 2, 3), states=("active", "inactive", "active"),
        initial_state="active", final_state="active", observation_count=3,
        transition_count=2, changed_transition_count=2, unchanged_transition_count=0,
        definite_transition_count=2, indeterminate_transition_count=0,
    )
    trajectory = TemporalTrajectory(
        subject_type="person", subject_id="subject-1", kind=TemporalTrajectoryKind.REVERSAL,
        observation_count=3, distinct_state_count=2, transition_count=2,
        reversal_count=1, oscillation_count=0, history_count=1,
        has_divergence=False, has_incomplete_history=False, has_temporal_uncertainty=False,
    )
    result = analyze_evidence_backed_trajectory(history, trajectory)
    assert result.evidence_ids == (1, 2, 3)
    assert result.states == ("active", "inactive", "active")
    assert result.change_points.change_point_count == 2

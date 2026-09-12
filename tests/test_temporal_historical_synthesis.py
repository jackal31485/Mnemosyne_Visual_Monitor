from __future__ import annotations

from src.domain.temporal_evidence_backed_trajectory import EvidenceBackedTrajectoryAnalysis
from src.domain.temporal_historical_synthesis import synthesize_historical_trajectories
from src.domain.temporal_state_history import TemporalStateHistory
from src.domain.temporal_trajectory import TemporalTrajectory, TemporalTrajectoryKind
from src.domain.temporal_change_points import analyze_change_points


def analysis(states: tuple[str, ...], evidence: tuple[int, ...], kind: TemporalTrajectoryKind):
    trajectory = TemporalTrajectory(
        subject_type="person", subject_id="subject-1", kind=kind,
        observation_count=len(states), distinct_state_count=len(set(states)),
        transition_count=sum(a != b for a, b in zip(states, states[1:])),
        reversal_count=0, oscillation_count=0, history_count=1,
        has_divergence=False, has_incomplete_history=False, has_temporal_uncertainty=False,
    )
    return EvidenceBackedTrajectoryAnalysis(
        subject_type="person", subject_id="subject-1", trajectory=trajectory,
        evidence_ids=evidence, states=states,
        change_points=analyze_change_points(trajectory, states),
    )


def test_historical_synthesis_is_deterministic():
    result = synthesize_historical_trajectories([
        analysis(("inactive", "inactive"), (2, 3), TemporalTrajectoryKind.STABLE),
        analysis(("active", "inactive"), (4, 5), TemporalTrajectoryKind.TRANSITION),
    ])
    assert result.analysis_count == 2
    assert result.observation_count == 4
    assert result.evidence_count == 4
    assert result.distinct_states == ("active", "inactive")
    assert result.trajectory_kinds == ("stable", "transition")
    assert result.change_point_count == 1
    assert result.persistent_change_point_count == 0
    assert result.evidence_coverage == 1.0

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_state_history import TemporalStateHistory
from .temporal_trajectory import TemporalTrajectory
from .temporal_change_points import TemporalChangePointAnalysis, analyze_change_points


@dataclass(frozen=True, slots=True)
class EvidenceBackedTrajectoryAnalysis:
    """Trajectory analysis retaining the evidence identifiers supporting it."""

    subject_type: str
    subject_id: str
    trajectory: TemporalTrajectory
    evidence_ids: tuple[int, ...]
    states: tuple[str, ...]
    change_points: TemporalChangePointAnalysis

    def __post_init__(self) -> None:
        if not self.subject_type or not self.subject_id:
            raise ValueError("subject identity must be non-empty")
        if self.trajectory.subject_type != self.subject_type or self.trajectory.subject_id != self.subject_id:
            raise ValueError("trajectory identity must match analysis identity")
        if len(self.evidence_ids) != self.trajectory.observation_count:
            raise ValueError("evidence_ids must match observation count")
        if len(self.states) != self.trajectory.observation_count:
            raise ValueError("states must match observation count")
        if any(evidence_id <= 0 for evidence_id in self.evidence_ids):
            raise ValueError("evidence IDs must be positive")

    @property
    def observation_count(self) -> int:
        return len(self.states)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_ids)

    @property
    def has_change_points(self) -> bool:
        return self.change_points.has_change_points


def analyze_evidence_backed_trajectory(
    history: TemporalStateHistory,
    trajectory: TemporalTrajectory,
) -> EvidenceBackedTrajectoryAnalysis:
    if not isinstance(history, TemporalStateHistory):
        raise TypeError("history must be a TemporalStateHistory")
    if not isinstance(trajectory, TemporalTrajectory):
        raise TypeError("trajectory must be a TemporalTrajectory")
    if (history.subject_type, history.subject_id) != (trajectory.subject_type, trajectory.subject_id):
        raise ValueError("history and trajectory must describe the same subject")
    if history.observation_count != trajectory.observation_count:
        raise ValueError("history and trajectory observation counts must match")
    states = tuple(history.states)
    change_points = analyze_change_points(trajectory, states)
    return EvidenceBackedTrajectoryAnalysis(
        subject_type=history.subject_type,
        subject_id=history.subject_id,
        trajectory=trajectory,
        evidence_ids=tuple(history.evidence_ids),
        states=states,
        change_points=change_points,
    )


def analyze_evidence_backed_trajectory_groups(
    pairs_by_subject: dict[tuple[str, str], tuple[TemporalStateHistory, TemporalTrajectory]],
) -> dict[tuple[str, str], EvidenceBackedTrajectoryAnalysis]:
    return {
        subject: analyze_evidence_backed_trajectory(*pairs_by_subject[subject])
        for subject in sorted(pairs_by_subject)
    }

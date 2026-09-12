from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_evidence_backed_trajectory import EvidenceBackedTrajectoryAnalysis
from .temporal_change_point_significance import analyze_change_point_significance


@dataclass(frozen=True, slots=True)
class TemporalHistoricalSynthesis:
    """Descriptive historical summary across evidence-backed trajectories."""

    subject_type: str
    subject_id: str
    analysis_count: int
    observation_count: int
    evidence_count: int
    distinct_states: tuple[str, ...]
    change_point_count: int
    persistent_change_point_count: int
    longest_stable_run: int
    trajectory_kinds: tuple[str, ...]
    has_uncertainty: bool
    has_incompleteness: bool
    has_divergence: bool

    def __post_init__(self) -> None:
        if not self.subject_type or not self.subject_id:
            raise ValueError("subject identity must be non-empty")
        if self.analysis_count < 1:
            raise ValueError("analysis_count must be positive")
        if min(self.observation_count, self.evidence_count, self.change_point_count, self.persistent_change_point_count, self.longest_stable_run) < 0:
            raise ValueError("counts must not be negative")

    @property
    def evidence_coverage(self) -> float:
        if self.observation_count == 0:
            return 0.0
        return self.evidence_count / self.observation_count

    @property
    def has_multiple_trajectory_kinds(self) -> bool:
        return len(self.trajectory_kinds) > 1


def synthesize_historical_trajectories(
    analyses: Iterable[EvidenceBackedTrajectoryAnalysis],
) -> TemporalHistoricalSynthesis:
    values = tuple(analyses)
    if not values:
        raise ValueError("analyses must not be empty")
    subject = (values[0].subject_type, values[0].subject_id)
    for analysis in values:
        if not isinstance(analysis, EvidenceBackedTrajectoryAnalysis):
            raise TypeError("analyses must contain EvidenceBackedTrajectoryAnalysis values")
        if (analysis.subject_type, analysis.subject_id) != subject:
            raise ValueError("analyses must describe the same subject")

    states: list[str] = []
    kinds: list[str] = []
    for analysis in values:
        for state in analysis.states:
            if state not in states:
                states.append(state)
        kind = analysis.trajectory.kind.value
        if kind not in kinds:
            kinds.append(kind)

    return TemporalHistoricalSynthesis(
        subject_type=subject[0],
        subject_id=subject[1],
        analysis_count=len(values),
        observation_count=sum(a.observation_count for a in values),
        evidence_count=sum(a.evidence_count for a in values),
        distinct_states=tuple(sorted(states)),
        change_point_count=sum(a.change_points.change_point_count for a in values),
        persistent_change_point_count=sum(
            analyze_change_point_significance(a.change_points).persistent_change_point_count
            for a in values
        ),
        longest_stable_run=max((a.change_points.longest_stable_run for a in values), default=0),
        trajectory_kinds=tuple(sorted(kinds)),
        has_uncertainty=any(a.trajectory.has_temporal_uncertainty for a in values),
        has_incompleteness=any(a.trajectory.has_incomplete_history for a in values),
        has_divergence=any(a.trajectory.has_divergence for a in values),
    )

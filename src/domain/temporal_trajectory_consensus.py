from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_trajectory import TemporalTrajectory, TemporalTrajectoryKind


@dataclass(frozen=True, slots=True)
class TemporalTrajectoryPosition:
    """Descriptive support for a trajectory classification."""

    kind: TemporalTrajectoryKind
    supporting_trajectory_count: int
    total_trajectory_count: int

    def __post_init__(self) -> None:
        if self.supporting_trajectory_count < 1:
            raise ValueError("supporting_trajectory_count must be positive")
        if self.total_trajectory_count < 1:
            raise ValueError("total_trajectory_count must be positive")
        if self.supporting_trajectory_count > self.total_trajectory_count:
            raise ValueError(
                "supporting_trajectory_count cannot exceed total_trajectory_count"
            )

    @property
    def support_ratio(self) -> float:
        return (
            self.supporting_trajectory_count
            / self.total_trajectory_count
        )


@dataclass(frozen=True, slots=True)
class TemporalTrajectoryConsensus:
    """Descriptive consensus summary across trajectories for one subject."""

    subject_type: str
    subject_id: str
    trajectory_count: int
    positions: tuple[TemporalTrajectoryPosition, ...]
    consensus_trajectory_count: int
    disagreement_trajectory_count: int
    has_disagreement: bool
    has_temporal_uncertainty: bool
    has_incompleteness: bool

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must not be empty")
        if not self.subject_id:
            raise ValueError("subject_id must not be empty")
        if self.trajectory_count < 1:
            raise ValueError("trajectory_count must be positive")
        if self.consensus_trajectory_count < 0:
            raise ValueError("consensus_trajectory_count must not be negative")
        if self.disagreement_trajectory_count < 0:
            raise ValueError(
                "disagreement_trajectory_count must not be negative"
            )

    @property
    def kind_count(self) -> int:
        return len(self.positions)

    @property
    def has_consensus(self) -> bool:
        return (
            self.trajectory_count > 0
            and self.kind_count == 1
            and not self.has_disagreement
        )

    @property
    def is_uncertain(self) -> bool:
        return self.has_temporal_uncertainty

    @property
    def is_incomplete(self) -> bool:
        return self.has_incompleteness

    @property
    def consensus_ratio(self) -> float:
        if self.trajectory_count == 0:
            return 0.0
        return self.consensus_trajectory_count / self.trajectory_count

    @property
    def disagreement_ratio(self) -> float:
        if self.trajectory_count == 0:
            return 0.0
        return self.disagreement_trajectory_count / self.trajectory_count


def _assert_trajectory(value: object) -> None:
    if not isinstance(value, TemporalTrajectory):
        raise TypeError("trajectory must be a TemporalTrajectory")


def analyze_trajectory_consensus(
    trajectories: Iterable[TemporalTrajectory],
) -> TemporalTrajectoryConsensus:
    """Describe agreement and disagreement across trajectories."""

    trajectories = tuple(trajectories)

    if not trajectories:
        raise ValueError("trajectories must not be empty")

    for trajectory in trajectories:
        _assert_trajectory(trajectory)

    subject_type = trajectories[0].subject_type
    subject_id = trajectories[0].subject_id

    for trajectory in trajectories[1:]:
        if (
            trajectory.subject_type != subject_type
            or trajectory.subject_id != subject_id
        ):
            raise ValueError(
                "trajectories must describe the same subject"
            )

    counts: dict[TemporalTrajectoryKind, int] = {}

    for trajectory in trajectories:
        counts[trajectory.kind] = counts.get(trajectory.kind, 0) + 1

    positions = tuple(
        TemporalTrajectoryPosition(
            kind=kind,
            supporting_trajectory_count=count,
            total_trajectory_count=len(trajectories),
        )
        for kind, count in counts.items()
    )

    has_disagreement = len(positions) > 1

    return TemporalTrajectoryConsensus(
        subject_type=subject_type,
        subject_id=subject_id,
        trajectory_count=len(trajectories),
        positions=positions,
        consensus_trajectory_count=(
            positions[0].supporting_trajectory_count
            if len(positions) == 1
            else max(position.supporting_trajectory_count for position in positions)
        ),
        disagreement_trajectory_count=(
            0
            if len(positions) == 1
            else len(trajectories)
            - max(position.supporting_trajectory_count for position in positions)
        ),
        has_disagreement=has_disagreement,
        has_temporal_uncertainty=any(
            trajectory.has_temporal_uncertainty
            for trajectory in trajectories
        ),
        has_incompleteness=any(
            trajectory.has_incomplete_history
            for trajectory in trajectories
        ),
    )


def analyze_trajectory_consensus_groups(
    trajectories_by_subject: dict[
        tuple[str, str],
        Iterable[TemporalTrajectory],
    ],
) -> dict[tuple[str, str], TemporalTrajectoryConsensus]:
    """Analyze trajectory consensus in deterministic subject-key order."""

    result: dict[
        tuple[str, str],
        TemporalTrajectoryConsensus,
    ] = {}

    for subject in sorted(trajectories_by_subject):
        result[subject] = analyze_trajectory_consensus(
            trajectories_by_subject[subject]
        )

    return result

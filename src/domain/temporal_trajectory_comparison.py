from __future__ import annotations

from dataclasses import dataclass

from .temporal_trajectory import (
    TemporalTrajectory,
    TemporalTrajectoryKind,
)


@dataclass(frozen=True, slots=True)
class TemporalTrajectoryComparison:
    """Deterministic descriptive comparison of two temporal trajectories."""

    subject_type: str
    subject_id: str

    left_kind: TemporalTrajectoryKind
    right_kind: TemporalTrajectoryKind

    same_kind: bool

    left_observation_count: int
    right_observation_count: int

    left_distinct_state_count: int
    right_distinct_state_count: int

    left_transition_count: int
    right_transition_count: int

    left_reversal_count: int
    right_reversal_count: int

    left_oscillation_count: int
    right_oscillation_count: int

    kind_divergence: bool
    observation_divergence: bool
    state_divergence: bool
    transition_divergence: bool
    reversal_divergence: bool
    oscillation_divergence: bool

    uncertainty_divergence: bool
    incompleteness_divergence: bool
    divergence_flag_difference: bool

    @property
    def has_difference(self) -> bool:
        return any(
            (
                self.kind_divergence,
                self.observation_divergence,
                self.state_divergence,
                self.transition_divergence,
                self.reversal_divergence,
                self.oscillation_divergence,
                self.uncertainty_divergence,
                self.incompleteness_divergence,
                self.divergence_flag_difference,
            )
        )

    @property
    def is_equivalent(self) -> bool:
        return not self.has_difference

    @property
    def has_kind_agreement(self) -> bool:
        return self.same_kind

    @property
    def has_trajectory_divergence(self) -> bool:
        return self.kind_divergence

    @property
    def has_uncertainty_difference(self) -> bool:
        return self.uncertainty_divergence

    @property
    def has_incompleteness_difference(self) -> bool:
        return self.incompleteness_divergence


def _assert_trajectory(value: TemporalTrajectory) -> None:
    if not isinstance(value, TemporalTrajectory):
        raise TypeError("trajectory must be a TemporalTrajectory")


def compare_trajectories(
    left: TemporalTrajectory,
    right: TemporalTrajectory,
) -> TemporalTrajectoryComparison:
    """Compare two trajectories without selecting either as authoritative."""
    _assert_trajectory(left)
    _assert_trajectory(right)

    if (
        left.subject_type != right.subject_type
        or left.subject_id != right.subject_id
    ):
        raise ValueError(
            "trajectories must describe the same subject"
        )

    return TemporalTrajectoryComparison(
        subject_type=left.subject_type,
        subject_id=left.subject_id,
        left_kind=left.kind,
        right_kind=right.kind,
        same_kind=left.kind is right.kind,
        left_observation_count=left.observation_count,
        right_observation_count=right.observation_count,
        left_distinct_state_count=left.distinct_state_count,
        right_distinct_state_count=right.distinct_state_count,
        left_transition_count=left.transition_count,
        right_transition_count=right.transition_count,
        left_reversal_count=left.reversal_count,
        right_reversal_count=right.reversal_count,
        left_oscillation_count=left.oscillation_count,
        right_oscillation_count=right.oscillation_count,
        kind_divergence=left.kind is not right.kind,
        observation_divergence=(
            left.observation_count != right.observation_count
        ),
        state_divergence=(
            left.distinct_state_count != right.distinct_state_count
        ),
        transition_divergence=(
            left.transition_count != right.transition_count
        ),
        reversal_divergence=(
            left.reversal_count != right.reversal_count
        ),
        oscillation_divergence=(
            left.oscillation_count != right.oscillation_count
        ),
        uncertainty_divergence=(
            left.has_temporal_uncertainty
            != right.has_temporal_uncertainty
        ),
        incompleteness_divergence=(
            left.has_incomplete_history
            != right.has_incomplete_history
        ),
        divergence_flag_difference=(
            left.has_divergence != right.has_divergence
        ),
    )


def compare_trajectory_groups(
    trajectories_by_subject: dict[
        tuple[str, str],
        tuple[TemporalTrajectory, TemporalTrajectory],
    ],
) -> dict[tuple[str, str], TemporalTrajectoryComparison]:
    """Compare trajectory pairs in deterministic subject-key order."""
    result: dict[
        tuple[str, str],
        TemporalTrajectoryComparison,
    ] = {}

    for subject in sorted(trajectories_by_subject):
        left, right = trajectories_by_subject[subject]
        result[subject] = compare_trajectories(left, right)

    return result

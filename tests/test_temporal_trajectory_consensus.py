from __future__ import annotations

import pytest

from src.domain.temporal_trajectory import (
    TemporalTrajectory,
    TemporalTrajectoryKind,
)
from src.domain.temporal_trajectory_consensus import (
    TemporalTrajectoryConsensus,
    TemporalTrajectoryPosition,
    analyze_trajectory_consensus,
    analyze_trajectory_consensus_groups,
)


def trajectory(
    kind: TemporalTrajectoryKind,
    *,
    uncertainty: bool = False,
    incomplete: bool = False,
) -> TemporalTrajectory:
    return TemporalTrajectory(
        subject_type="person",
        subject_id="subject-1",
        kind=kind,
        observation_count=2,
        distinct_state_count=2,
        transition_count=1,
        reversal_count=0,
        oscillation_count=0,
        history_count=1,
        has_divergence=False,
        has_incomplete_history=incomplete,
        has_temporal_uncertainty=uncertainty,
    )


def test_position_validates_support_counts():
    with pytest.raises(ValueError):
        TemporalTrajectoryPosition(
            TemporalTrajectoryKind.STABLE,
            0,
            1,
        )

    with pytest.raises(ValueError):
        TemporalTrajectoryPosition(
            TemporalTrajectoryKind.STABLE,
            2,
            1,
        )


def test_position_support_ratio():
    position = TemporalTrajectoryPosition(
        TemporalTrajectoryKind.REVERSAL,
        2,
        3,
    )

    assert position.support_ratio == pytest.approx(2 / 3)


def test_single_trajectory_is_consensus():
    result = analyze_trajectory_consensus(
        [trajectory(TemporalTrajectoryKind.STABLE)]
    )

    assert isinstance(result, TemporalTrajectoryConsensus)
    assert result.trajectory_count == 1
    assert result.kind_count == 1
    assert result.has_consensus
    assert not result.has_disagreement
    assert result.consensus_trajectory_count == 1
    assert result.disagreement_trajectory_count == 0


def test_identical_trajectories_are_consensus():
    result = analyze_trajectory_consensus(
        [
            trajectory(TemporalTrajectoryKind.REVERSAL),
            trajectory(TemporalTrajectoryKind.REVERSAL),
            trajectory(TemporalTrajectoryKind.REVERSAL),
        ]
    )

    assert result.has_consensus
    assert result.kind_count == 1
    assert result.positions[0].kind is TemporalTrajectoryKind.REVERSAL
    assert result.positions[0].supporting_trajectory_count == 3
    assert result.consensus_ratio == 1.0
    assert result.disagreement_ratio == 0.0


def test_different_trajectories_are_reported_as_disagreement():
    result = analyze_trajectory_consensus(
        [
            trajectory(TemporalTrajectoryKind.REVERSAL),
            trajectory(TemporalTrajectoryKind.TRANSITION),
        ]
    )

    assert not result.has_consensus
    assert result.has_disagreement
    assert result.kind_count == 2
    assert result.consensus_trajectory_count == 1
    assert result.disagreement_trajectory_count == 1


def test_majority_is_descriptive_not_consensus():
    result = analyze_trajectory_consensus(
        [
            trajectory(TemporalTrajectoryKind.REVERSAL),
            trajectory(TemporalTrajectoryKind.REVERSAL),
            trajectory(TemporalTrajectoryKind.TRANSITION),
        ]
    )

    assert result.has_disagreement
    assert not result.has_consensus
    assert result.consensus_trajectory_count == 2
    assert result.disagreement_trajectory_count == 1
    assert result.positions[0].supporting_trajectory_count == 2


def test_position_order_is_first_seen_order():
    result = analyze_trajectory_consensus(
        [
            trajectory(TemporalTrajectoryKind.TRANSITION),
            trajectory(TemporalTrajectoryKind.REVERSAL),
            trajectory(TemporalTrajectoryKind.TRANSITION),
        ]
    )

    assert [position.kind for position in result.positions] == [
        TemporalTrajectoryKind.TRANSITION,
        TemporalTrajectoryKind.REVERSAL,
    ]


def test_uncertainty_is_propagated():
    result = analyze_trajectory_consensus(
        [
            trajectory(TemporalTrajectoryKind.TRANSITION, uncertainty=True),
            trajectory(TemporalTrajectoryKind.TRANSITION),
        ]
    )

    assert result.has_temporal_uncertainty
    assert result.is_uncertain


def test_incompleteness_is_propagated():
    result = analyze_trajectory_consensus(
        [
            trajectory(TemporalTrajectoryKind.STABLE, incomplete=True),
            trajectory(TemporalTrajectoryKind.STABLE),
        ]
    )

    assert result.has_incompleteness
    assert result.is_incomplete


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        analyze_trajectory_consensus([])


def test_mixed_subjects_are_rejected():
    first = trajectory(TemporalTrajectoryKind.STABLE)
    second = TemporalTrajectory(
        subject_type="organization",
        subject_id="other",
        kind=TemporalTrajectoryKind.STABLE,
        observation_count=1,
        distinct_state_count=1,
        transition_count=0,
        reversal_count=0,
        oscillation_count=0,
        history_count=1,
        has_divergence=False,
        has_incomplete_history=False,
        has_temporal_uncertainty=False,
    )

    with pytest.raises(ValueError):
        analyze_trajectory_consensus([first, second])


def test_invalid_trajectory_type_is_rejected():
    with pytest.raises(TypeError):
        analyze_trajectory_consensus([object()])  # type: ignore[list-item]


def test_groups_are_deterministic():
    first = trajectory(TemporalTrajectoryKind.STABLE)
    second = TemporalTrajectory(
        subject_type="person",
        subject_id="subject-2",
        kind=TemporalTrajectoryKind.REVERSAL,
        observation_count=2,
        distinct_state_count=2,
        transition_count=1,
        reversal_count=0,
        oscillation_count=0,
        history_count=1,
        has_divergence=False,
        has_incomplete_history=False,
        has_temporal_uncertainty=False,
    )

    result = analyze_trajectory_consensus_groups(
        {
            ("person", "subject-2"): [second],
            ("person", "subject-1"): [first],
        }
    )

    assert list(result) == [
        ("person", "subject-1"),
        ("person", "subject-2"),
    ]

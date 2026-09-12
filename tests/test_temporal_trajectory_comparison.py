from __future__ import annotations

import pytest

from src.domain.temporal_trajectory import (
    TemporalTrajectoryKind,
    classify_trajectory,
)
from src.domain.temporal_trajectory_comparison import (
    TemporalTrajectoryComparison,
    compare_trajectories,
    compare_trajectory_groups,
)
from src.domain.temporal_state_history import TemporalStateHistory


def history(
    states,
    *,
    subject_id="subject-1",
    evidence_ids=None,
    indeterminate_transition_count=0,
):
    states = tuple(states)

    if evidence_ids is None:
        evidence_ids = tuple(index + 1 for index in range(len(states)))
    else:
        evidence_ids = tuple(evidence_ids)

    transition_count = max(0, len(states) - 1)
    changed_transition_count = sum(
        left != right
        for left, right in zip(states, states[1:])
    )
    unchanged_transition_count = (
        transition_count - changed_transition_count
    )

    if indeterminate_transition_count > transition_count:
        raise ValueError("invalid indeterminate transition count")

    definite_transition_count = (
        transition_count - indeterminate_transition_count
    )

    return TemporalStateHistory(
        subject_type="person",
        subject_id=subject_id,
        evidence_ids=evidence_ids,
        states=states,
        initial_state=states[0] if states else None,
        final_state=states[-1] if states else None,
        observation_count=len(states),
        transition_count=transition_count,
        changed_transition_count=changed_transition_count,
        unchanged_transition_count=unchanged_transition_count,
        definite_transition_count=definite_transition_count,
        indeterminate_transition_count=indeterminate_transition_count,
    )


def trajectory(
    states,
    *,
    subject_id="subject-1",
    indeterminate_transition_count=0,
):
    return classify_trajectory(
        [
            history(
                states,
                subject_id=subject_id,
                indeterminate_transition_count=(
                    indeterminate_transition_count
                ),
            )
        ]
    )


def test_identical_trajectories_are_equivalent():
    first = trajectory(["active", "active"])
    second = trajectory(["active", "active"])

    result = compare_trajectories(first, second)

    assert isinstance(result, TemporalTrajectoryComparison)
    assert result.same_kind
    assert not result.has_difference
    assert result.is_equivalent


def test_different_kinds_are_trajectory_divergence():
    first = trajectory(["active", "inactive"])
    second = trajectory(["active", "inactive", "active"])

    result = compare_trajectories(first, second)

    assert result.left_kind is TemporalTrajectoryKind.TRANSITION
    assert result.right_kind is TemporalTrajectoryKind.REVERSAL
    assert result.kind_divergence
    assert result.has_trajectory_divergence
    assert result.has_difference


def test_same_kind_can_still_have_metric_differences():
    first = trajectory(["draft", "review"])
    second = trajectory(["draft", "review", "published"])

    result = compare_trajectories(first, second)

    assert result.same_kind
    assert not result.kind_divergence
    assert result.observation_divergence
    assert result.state_divergence
    assert not result.is_equivalent


def test_reversal_and_transition_counts_are_preserved_when_history_extends():
    first = trajectory(["active", "inactive", "active"])
    second = trajectory(["active", "inactive", "active", "active"])

    result = compare_trajectories(first, second)

    assert not result.reversal_divergence
    assert not result.transition_divergence
    assert result.left_reversal_count == 1
    assert result.right_reversal_count == 1
    assert result.left_transition_count == 2
    assert result.right_transition_count == 2
    assert result.observation_divergence


def test_oscillation_count_difference_is_reported():
    first = trajectory(
        ["active", "inactive", "active", "inactive"]
    )
    second = trajectory(
        ["active", "inactive", "active", "inactive", "active"]
    )

    result = compare_trajectories(first, second)

    assert result.oscillation_divergence
    assert result.left_oscillation_count == 1
    assert result.right_oscillation_count == 2


def test_uncertainty_difference_is_reported():
    first = trajectory(
        ["active", "inactive"],
        indeterminate_transition_count=1,
    )
    second = trajectory(["active", "inactive"])

    result = compare_trajectories(first, second)

    assert result.uncertainty_divergence
    assert result.has_uncertainty_difference


def test_incompleteness_difference_is_reported():
    first = trajectory(["active", "inactive"])
    second = trajectory(["active", "inactive"])

    # Both trajectories are complete here; the comparison should therefore
    # report no incompleteness difference.
    result = compare_trajectories(first, second)

    assert not result.incompleteness_divergence
    assert not result.has_incompleteness_difference


def test_divergence_flag_difference_is_reported():
    first = classify_trajectory(
        [
            history(["active", "inactive"]),
            history(["active", "inactive"]),
        ]
    )
    second = classify_trajectory(
        [
            history(["active", "inactive"]),
            history(["active", "active"]),
        ]
    )

    result = compare_trajectories(first, second)

    assert result.divergence_flag_difference


def test_subject_mismatch_is_rejected():
    first = trajectory(["active"], subject_id="subject-1")
    second = trajectory(["active"], subject_id="subject-2")

    with pytest.raises(ValueError, match="same subject"):
        compare_trajectories(first, second)


def test_invalid_left_type_is_rejected():
    right = trajectory(["active"])

    with pytest.raises(TypeError, match="TemporalTrajectory"):
        compare_trajectories(object(), right)


def test_invalid_right_type_is_rejected():
    left = trajectory(["active"])

    with pytest.raises(TypeError, match="TemporalTrajectory"):
        compare_trajectories(left, object())


def test_group_comparison_is_deterministic():
    first_a = trajectory(["active"], subject_id="a")
    second_a = trajectory(["active", "inactive"], subject_id="a")

    first_b = trajectory(["active"], subject_id="b")
    second_b = trajectory(["active"], subject_id="b")

    result = compare_trajectory_groups(
        {
            ("person", "b"): (first_b, second_b),
            ("person", "a"): (first_a, second_a),
        }
    )

    assert list(result) == [
        ("person", "a"),
        ("person", "b"),
    ]
    assert result[("person", "a")].kind_divergence
    assert result[("person", "b")].is_equivalent


def test_group_comparison_preserves_subject_validation():
    first = trajectory(["active"], subject_id="a")
    second = trajectory(["active"], subject_id="b")

    with pytest.raises(ValueError, match="same subject"):
        compare_trajectory_groups(
            {
                ("person", "a"): (first, second),
            }
        )

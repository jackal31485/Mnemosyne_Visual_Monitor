from __future__ import annotations

import pytest

from src.domain.temporal_state_history import TemporalStateHistory
from src.domain.temporal_trajectory import (
    TemporalTrajectoryKind,
    classify_trajectory,
    classify_trajectory_groups,
)


def history(states, *, subject_id="subject-1", evidence_ids=None):
    states = tuple(states)

    if evidence_ids is None:
        evidence_ids = tuple(
            index + 1
            for index in range(len(states))
        )
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
        definite_transition_count=transition_count,
        indeterminate_transition_count=0,
    )


def test_stable_history():
    result = classify_trajectory(
        [history(["active", "active", "active"])]
    )

    assert result.kind is TemporalTrajectoryKind.STABLE
    assert result.is_stable
    assert result.transition_count == 0
    assert result.distinct_state_count == 1


def test_single_transition():
    result = classify_trajectory(
        [history(["active", "inactive"])]
    )

    assert result.kind is TemporalTrajectoryKind.TRANSITION
    assert result.transition_count == 1
    assert result.distinct_state_count == 2


def test_repeated_state_return_is_reversal():
    result = classify_trajectory(
        [history(["active", "inactive", "active"])]
    )

    assert result.kind is TemporalTrajectoryKind.REVERSAL
    assert result.reversal_count == 1


def test_repeated_cycle_is_oscillation():
    result = classify_trajectory(
        [history(["active", "inactive", "active", "inactive"])]
    )

    assert result.kind is TemporalTrajectoryKind.OSCILLATION
    assert result.oscillation_count == 1
    assert result.reversal_count >= 1


def test_multi_transition_without_reversal_is_transition():
    result = classify_trajectory(
        [history(["draft", "review", "published"])]
    )

    assert result.kind is TemporalTrajectoryKind.TRANSITION
    assert result.transition_count == 2


def test_divergence_takes_precedence_over_single_history_shape():
    result = classify_trajectory(
        [
            history(["active", "inactive"]),
            history(["active", "active"]),
        ]
    )

    assert result.kind is TemporalTrajectoryKind.DIVERGENT
    assert result.has_divergence
    assert result.history_count == 2


def test_incomplete_history_is_not_disagreement():
    result = classify_trajectory(
        [
            history(["active", "inactive"]),
            history(["active"]),
        ]
    )

    assert result.kind is TemporalTrajectoryKind.INCOMPLETE
    assert result.has_incomplete_history


def test_temporal_uncertainty_is_propagated():
    first = history(["active", "inactive"])
    second = history(["active", "inactive"])

    # The history object itself carries the uncertainty counts used by
    # the existing temporal-history synthesis layer.
    second = TemporalStateHistory(
        subject_type=second.subject_type,
        subject_id=second.subject_id,
        evidence_ids=second.evidence_ids,
        states=second.states,
        initial_state=second.initial_state,
        final_state=second.final_state,
        observation_count=second.observation_count,
        transition_count=second.transition_count,
        changed_transition_count=second.changed_transition_count,
        unchanged_transition_count=second.unchanged_transition_count,
        definite_transition_count=0,
        indeterminate_transition_count=1,
    )

    result = classify_trajectory([first, second])

    assert result.has_temporal_uncertainty
    assert result.kind is TemporalTrajectoryKind.UNCERTAIN


def test_empty_history():
    result = classify_trajectory([history([])])

    assert result.kind is TemporalTrajectoryKind.EMPTY
    assert result.observation_count == 0


def test_same_subject_is_required_by_synthesis():
    with pytest.raises(ValueError):
        classify_trajectory(
            [
                history(["active"], subject_id="one"),
                history(["active"], subject_id="two"),
            ]
        )


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        classify_trajectory([])


def test_groups_are_deterministic():
    histories = {
        ("person", "b"): [history(["active"], subject_id="b")],
        ("person", "a"): [history(["active"], subject_id="a")],
    }

    result = classify_trajectory_groups(histories)

    assert list(result) == [
        ("person", "a"),
        ("person", "b"),
    ]


def test_majority_is_not_treated_as_consensus():
    result = classify_trajectory(
        [
            history(["active", "active"]),
            history(["active", "active"]),
            history(["active", "inactive"]),
        ]
    )

    assert result.has_divergence
    assert result.kind is TemporalTrajectoryKind.DIVERGENT

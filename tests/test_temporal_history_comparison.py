from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.temporal_state_history import TemporalStateHistory
from src.domain.temporal_history_comparison import (
    compare_state_histories,
    compare_state_history_pairs,
)


def history(
    *,
    subject_type: str = "entity",
    subject_id: str = "alpha",
    evidence_ids: tuple[int, ...] | None = None,
    states: tuple[str, ...] = ("draft", "active", "retired"),
    indeterminate_transition_count: int = 0,
) -> TemporalStateHistory:
    if evidence_ids is None:
        evidence_ids = tuple(range(1, len(states) + 1))

    observation_count = len(states)
    transition_count = max(0, observation_count - 1)

    return TemporalStateHistory(
        subject_type=subject_type,
        subject_id=subject_id,
        evidence_ids=evidence_ids,
        states=states,
        initial_state=states[0] if states else None,
        final_state=states[-1] if states else None,
        observation_count=observation_count,
        transition_count=transition_count,
        changed_transition_count=transition_count,
        unchanged_transition_count=0,
        definite_transition_count=(
            transition_count - indeterminate_transition_count
        ),
        indeterminate_transition_count=indeterminate_transition_count,
    )


def test_matching_histories_are_compared_positionally() -> None:
    result = compare_state_histories(
        history(),
        history(evidence_ids=(10, 11, 12)),
    )

    assert result.shared_state_count == 3
    assert result.divergent_state_count == 0
    assert result.matching_states == (
        (1, 10, "draft"),
        (2, 11, "active"),
        (3, 12, "retired"),
    )


def test_different_states_are_reported_as_divergence() -> None:
    result = compare_state_histories(
        history(states=("draft", "active", "retired")),
        history(
            evidence_ids=(10, 11, 12),
            states=("draft", "paused", "retired"),
        ),
    )

    assert result.shared_state_count == 2
    assert result.divergent_state_count == 1
    assert result.divergent_states == (
        (2, 11, "active", "paused"),
    )


def test_left_longer_history_preserves_left_only_observations() -> None:
    result = compare_state_histories(
        history(
            evidence_ids=(1, 2, 3),
            states=("draft", "active", "retired"),
        ),
        history(
            evidence_ids=(10, 20),
            states=("draft", "active"),
        ),
    )

    assert result.left_only_states == (
        (3, "retired"),
    )
    assert result.right_only_states == ()
    assert result.divergent_states[-1] == (
        3,
        None,
        "retired",
        None,
    )


def test_right_longer_history_preserves_right_only_observations() -> None:
    result = compare_state_histories(
        history(
            evidence_ids=(1, 2),
            states=("draft", "active"),
        ),
        history(
            evidence_ids=(10, 20, 30),
            states=("draft", "active", "retired"),
        ),
    )

    assert result.left_only_states == ()
    assert result.right_only_states == (
        (30, "retired"),
    )
    assert result.divergent_states[-1] == (
        None,
        30,
        None,
        "retired",
    )


def test_empty_histories_compare_cleanly() -> None:
    result = compare_state_histories(
        history(evidence_ids=(), states=()),
        history(evidence_ids=(), states=()),
    )

    assert result.comparison_count == 0
    assert result.matching_states == ()
    assert result.divergent_states == ()
    assert result.left_only_states == ()
    assert result.right_only_states == ()
    assert result.shared_state_count == 0
    assert result.divergent_state_count == 0
    assert not result.has_divergence


def test_empty_left_history_is_all_right_only() -> None:
    result = compare_state_histories(
        history(evidence_ids=(), states=()),
        history(
            evidence_ids=(10, 20),
            states=("draft", "active"),
        ),
    )

    assert result.left_only_states == ()
    assert result.right_only_states == (
        (10, "draft"),
        (20, "active"),
    )
    assert result.divergent_state_count == 2


def test_empty_right_history_is_all_left_only() -> None:
    result = compare_state_histories(
        history(
            evidence_ids=(1, 2),
            states=("draft", "active"),
        ),
        history(evidence_ids=(), states=()),
    )

    assert result.left_only_states == (
        (1, "draft"),
        (2, "active"),
    )
    assert result.right_only_states == ()
    assert result.divergent_state_count == 2


def test_same_subject_is_required() -> None:
    with pytest.raises(ValueError, match="same subject"):
        compare_state_histories(
            history(subject_id="alpha"),
            history(subject_id="beta"),
        )


def test_same_subject_type_is_required() -> None:
    with pytest.raises(ValueError, match="same subject"):
        compare_state_histories(
            history(subject_type="entity"),
            history(subject_type="memory"),
        )


def test_invalid_left_history_is_rejected() -> None:
    with pytest.raises(TypeError, match="TemporalStateHistory"):
        compare_state_histories("not a history", history())  # type: ignore[arg-type]


def test_invalid_right_history_is_rejected() -> None:
    with pytest.raises(TypeError, match="TemporalStateHistory"):
        compare_state_histories(history(), "not a history")  # type: ignore[arg-type]


def test_temporal_uncertainty_is_preserved() -> None:
    result = compare_state_histories(
        history(indeterminate_transition_count=1),
        history(),
    )

    assert result.temporal_uncertainty
    assert result.has_temporal_uncertainty


def test_definite_histories_have_no_temporal_uncertainty() -> None:
    result = compare_state_histories(
        history(),
        history(evidence_ids=(10, 11, 12)),
    )

    assert not result.temporal_uncertainty


def test_matching_states_are_not_divergence() -> None:
    result = compare_state_histories(
        history(states=("active",)),
        history(
            evidence_ids=(20,),
            states=("active",),
        ),
    )

    assert result.matching_states == (
        (1, 20, "active"),
    )
    assert result.divergent_states == ()


def test_comparison_is_immutable() -> None:
    result = compare_state_histories(history(), history())

    with pytest.raises(FrozenInstanceError):
        result.subject_id = "changed"  # type: ignore[misc]


def test_multiple_history_pairs_are_deterministically_sorted() -> None:
    first = history(
        subject_id="zeta",
        evidence_ids=(1,),
        states=("active",),
    )
    second = history(
        subject_id="alpha",
        evidence_ids=(2,),
        states=("draft",),
    )

    results = compare_state_history_pairs(
        (
            (first, first),
            (second, second),
        )
    )

    assert tuple(result.subject_id for result in results) == (
        "alpha",
        "zeta",
    )


def test_multiple_history_pairs_reject_invalid_subject_pair() -> None:
    left = history(subject_id="alpha")
    right = history(subject_id="beta")

    with pytest.raises(ValueError, match="same subject"):
        compare_state_history_pairs(((left, right),))


def test_comparison_count_uses_longer_history() -> None:
    result = compare_state_histories(
        history(
            evidence_ids=(1,),
            states=("draft",),
        ),
        history(
            evidence_ids=(10, 20, 30),
            states=("draft", "active", "retired"),
        ),
    )

    assert result.comparison_count == 3


def test_distinct_state_values_are_not_deduplicated() -> None:
    result = compare_state_histories(
        history(
            evidence_ids=(1, 2, 3),
            states=("active", "active", "retired"),
        ),
        history(
            evidence_ids=(10, 20, 30),
            states=("active", "active", "retired"),
        ),
    )

    assert result.matching_states == (
        (1, 10, "active"),
        (2, 20, "active"),
        (3, 30, "retired"),
    )
    assert result.shared_state_count == 3

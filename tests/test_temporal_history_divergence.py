from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.temporal_history_divergence import (
    TemporalHistoryDivergence,
    analyze_history_divergence,
    analyze_history_divergences,
    compare_and_analyze_history_divergence,
)
from src.domain.temporal_history_comparison import (
    compare_state_histories,
)
from src.domain.temporal_state_history import TemporalStateHistory


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


def test_fully_matching_histories_have_full_agreement() -> None:
    comparison = compare_state_histories(
        history(),
        history(evidence_ids=(10, 20, 30)),
    )

    result = analyze_history_divergence(comparison)

    assert result.comparison_count == 3
    assert result.shared_state_count == 3
    assert result.divergent_state_count == 0
    assert result.agreement_ratio == 1.0
    assert result.divergence_ratio == 0.0
    assert result.first_divergence_index is None
    assert result.is_fully_agreeing


def test_state_difference_is_divergence() -> None:
    comparison = compare_state_histories(
        history(states=("draft", "active", "retired")),
        history(
            evidence_ids=(10, 20, 30),
            states=("draft", "paused", "retired"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.shared_state_count == 2
    assert result.divergent_state_count == 1
    assert result.agreement_ratio == pytest.approx(2 / 3)
    assert result.divergence_ratio == pytest.approx(1 / 3)
    assert result.first_divergence_index == 1
    assert result.has_divergence


def test_left_only_observations_are_asymmetric() -> None:
    comparison = compare_state_histories(
        history(
            evidence_ids=(1, 2, 3),
            states=("draft", "active", "retired"),
        ),
        history(
            evidence_ids=(10, 20),
            states=("draft", "active"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.left_only_count == 1
    assert result.right_only_count == 0
    assert result.has_asymmetric_observations
    assert result.divergent_state_count == 1
    assert result.first_divergence_index == 2


def test_right_only_observations_are_asymmetric() -> None:
    comparison = compare_state_histories(
        history(
            evidence_ids=(1, 2),
            states=("draft", "active"),
        ),
        history(
            evidence_ids=(10, 20, 30),
            states=("draft", "active", "retired"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.left_only_count == 0
    assert result.right_only_count == 1
    assert result.has_asymmetric_observations
    assert result.first_divergence_index == 2


def test_empty_histories_produce_empty_analysis() -> None:
    comparison = compare_state_histories(
        history(evidence_ids=(), states=()),
        history(evidence_ids=(), states=()),
    )

    result = analyze_history_divergence(comparison)

    assert result.comparison_count == 0
    assert result.shared_state_count == 0
    assert result.divergent_state_count == 0
    assert result.agreement_ratio == 0.0
    assert result.divergence_ratio == 0.0
    assert result.first_divergence_index is None
    assert result.is_empty
    assert result.is_fully_agreeing


def test_temporal_uncertainty_is_preserved() -> None:
    comparison = compare_state_histories(
        history(indeterminate_transition_count=1),
        history(),
    )

    result = analyze_history_divergence(comparison)

    assert result.has_temporal_uncertainty


def test_uncertainty_does_not_create_divergence() -> None:
    comparison = compare_state_histories(
        history(indeterminate_transition_count=1),
        history(evidence_ids=(10, 20, 30)),
    )

    result = analyze_history_divergence(comparison)

    assert result.divergent_state_count == 0
    assert result.has_temporal_uncertainty
    assert not result.has_divergence


def test_compare_and_analyze_combines_both_operations() -> None:
    result = compare_and_analyze_history_divergence(
        history(states=("draft", "active")),
        history(
            evidence_ids=(10, 20),
            states=("draft", "paused"),
        ),
    )

    assert result.subject_id == "alpha"
    assert result.divergent_state_count == 1


def test_multiple_comparisons_are_sorted_deterministically() -> None:
    zeta = compare_state_histories(
        history(subject_id="zeta", evidence_ids=(1,), states=("active",)),
        history(subject_id="zeta", evidence_ids=(10,), states=("active",)),
    )
    alpha = compare_state_histories(
        history(subject_id="alpha", evidence_ids=(2,), states=("draft",)),
        history(subject_id="alpha", evidence_ids=(20,), states=("active",)),
    )

    results = analyze_history_divergences((zeta, alpha))

    assert tuple(result.subject_id for result in results) == (
        "alpha",
        "zeta",
    )


def test_invalid_comparison_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="TemporalHistoryComparison",
    ):
        analyze_history_divergence("invalid")  # type: ignore[arg-type]


def test_divergence_result_is_immutable() -> None:
    comparison = compare_state_histories(
        history(),
        history(evidence_ids=(10, 20, 30)),
    )

    result = analyze_history_divergence(comparison)

    with pytest.raises(FrozenInstanceError):
        result.subject_id = "changed"  # type: ignore[misc]


def test_divergence_flags_are_consistent() -> None:
    comparison = compare_state_histories(
        history(states=("draft", "active")),
        history(
            evidence_ids=(10, 20),
            states=("draft", "paused"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.has_divergence
    assert not result.is_fully_agreeing
    assert not result.has_asymmetric_observations


def test_multiple_divergences_use_first_positional_index() -> None:
    comparison = compare_state_histories(
        history(states=("draft", "active", "retired")),
        history(
            evidence_ids=(10, 20, 30),
            states=("paused", "active", "deleted"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.divergent_state_count == 2
    assert result.first_divergence_index == 0


def test_same_states_at_later_positions_do_not_hide_earlier_divergence() -> None:
    comparison = compare_state_histories(
        history(states=("draft", "active", "retired")),
        history(
            evidence_ids=(10, 20, 30),
            states=("draft", "paused", "retired"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.first_divergence_index == 1
    assert result.shared_state_count == 2


def test_ratio_values_are_bounded() -> None:
    comparison = compare_state_histories(
        history(states=("draft", "active")),
        history(
            evidence_ids=(10, 20),
            states=("paused", "retired"),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert 0.0 <= result.agreement_ratio <= 1.0
    assert 0.0 <= result.divergence_ratio <= 1.0


def test_subject_identity_is_preserved() -> None:
    comparison = compare_state_histories(
        history(subject_type="entity", subject_id="person-1"),
        history(
            subject_type="entity",
            subject_id="person-1",
            evidence_ids=(10, 20, 30),
        ),
    )

    result = analyze_history_divergence(comparison)

    assert result.subject_type == "entity"
    assert result.subject_id == "person-1"

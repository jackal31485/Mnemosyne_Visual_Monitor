from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.temporal_history_consensus import (
    TemporalConsensusPosition,
    TemporalHistoryConsensus,
    analyze_history_consensus,
    analyze_history_consensus_groups,
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

    transition_count = max(0, len(states) - 1)

    return TemporalStateHistory(
        subject_type=subject_type,
        subject_id=subject_id,
        evidence_ids=evidence_ids,
        states=states,
        initial_state=states[0] if states else None,
        final_state=states[-1] if states else None,
        observation_count=len(states),
        transition_count=transition_count,
        changed_transition_count=transition_count,
        unchanged_transition_count=0,
        definite_transition_count=(
            transition_count - indeterminate_transition_count
        ),
        indeterminate_transition_count=indeterminate_transition_count,
    )


def test_all_histories_agree() -> None:
    result = analyze_history_consensus(
        (
            history(),
            history(evidence_ids=(10, 20, 30)),
            history(evidence_ids=(100, 200, 300)),
        )
    )

    assert result.history_count == 3
    assert result.comparison_count == 3
    assert result.consensus_position_count == 3
    assert result.disagreement_position_count == 0
    assert result.incomplete_position_count == 0
    assert result.consensus_ratio == 1.0
    assert result.disagreement_ratio == 0.0
    assert not result.has_disagreement


def test_disagreement_is_identified_per_position() -> None:
    result = analyze_history_consensus(
        (
            history(states=("draft", "active", "retired")),
            history(
                evidence_ids=(10, 20, 30),
                states=("draft", "paused", "retired"),
            ),
            history(
                evidence_ids=(100, 200, 300),
                states=("draft", "active", "retired"),
            ),
        )
    )

    assert result.consensus_position_count == 2
    assert result.disagreement_position_count == 1
    assert result.positions[1].states == ("active", "paused")
    assert result.positions[1].supporting_history_count == 2
    assert result.has_disagreement


def test_majority_state_is_preserved_without_becoming_truth() -> None:
    result = analyze_history_consensus(
        (
            history(states=("draft",)),
            history(evidence_ids=(10,), states=("active",)),
            history(evidence_ids=(20,), states=("active",)),
        )
    )

    position = result.positions[0]

    assert position.states == ("draft", "active")
    assert position.supporting_history_count == 2
    assert position.total_history_count == 3
    assert result.disagreement_position_count == 1


def test_incomplete_history_is_separate_from_disagreement() -> None:
    result = analyze_history_consensus(
        (
            history(
                evidence_ids=(1, 2, 3),
                states=("draft", "active", "retired"),
            ),
            history(
                evidence_ids=(10, 20),
                states=("draft", "active"),
            ),
        )
    )

    assert result.incomplete_position_count == 1
    assert result.disagreement_position_count == 0
    assert result.consensus_position_count == 2
    assert result.has_incomplete_history
    assert not result.has_disagreement


def test_multiple_histories_can_have_different_lengths() -> None:
    result = analyze_history_consensus(
        (
            history(
                evidence_ids=(1,),
                states=("draft",),
            ),
            history(
                evidence_ids=(10, 20, 30),
                states=("draft", "active", "retired"),
            ),
            history(
                evidence_ids=(100, 200),
                states=("draft", "active"),
            ),
        )
    )

    assert result.comparison_count == 3
    assert result.incomplete_position_count == 2
    assert result.positions[0].states == ("draft",)
    assert result.positions[1].states == ("active",)
    assert result.positions[2].states == ("retired",)


def test_empty_history_can_be_analyzed_with_another_history() -> None:
    result = analyze_history_consensus(
        (
            history(evidence_ids=(), states=()),
            history(
                evidence_ids=(10, 20),
                states=("draft", "active"),
            ),
        )
    )

    assert result.comparison_count == 2
    assert result.incomplete_position_count == 2
    assert result.positions[0].states == ("draft",)
    assert result.positions[1].states == ("active",)


def test_empty_collection_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        analyze_history_consensus(())


def test_invalid_history_is_rejected() -> None:
    with pytest.raises(TypeError, match="TemporalStateHistory"):
        analyze_history_consensus(("invalid",))  # type: ignore[arg-type]


def test_different_subjects_are_rejected() -> None:
    with pytest.raises(ValueError, match="same subject"):
        analyze_history_consensus(
            (
                history(subject_id="alpha"),
                history(subject_id="beta"),
            )
        )


def test_temporal_uncertainty_is_preserved() -> None:
    result = analyze_history_consensus(
        (
            history(indeterminate_transition_count=1),
            history(evidence_ids=(10, 20, 30)),
        )
    )

    assert result.has_temporal_uncertainty


def test_consensus_position_is_immutable() -> None:
    position = TemporalConsensusPosition(
        index=0,
        states=("active",),
        supporting_history_count=2,
        total_history_count=2,
    )

    with pytest.raises(FrozenInstanceError):
        position.index = 1  # type: ignore[misc]


def test_consensus_result_is_immutable() -> None:
    result = analyze_history_consensus(
        (
            history(),
            history(evidence_ids=(10, 20, 30)),
        )
    )

    with pytest.raises(FrozenInstanceError):
        result.subject_id = "changed"  # type: ignore[misc]


def test_consensus_groups_are_sorted_deterministically() -> None:
    results = analyze_history_consensus_groups(
        (
            history(subject_id="zeta"),
            history(subject_id="alpha"),
            history(subject_id="zeta", evidence_ids=(10, 20, 30)),
            history(subject_id="alpha", evidence_ids=(40, 50, 60)),
        )
    )

    assert tuple(result.subject_id for result in results) == (
        "alpha",
        "zeta",
    )


def test_consensus_groups_empty_input_returns_empty_tuple() -> None:
    assert analyze_history_consensus_groups(()) == ()


def test_consensus_position_validates_supporting_count() -> None:
    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        TemporalConsensusPosition(
            index=0,
            states=("active",),
            supporting_history_count=3,
            total_history_count=2,
        )


def test_consensus_position_requires_state() -> None:
    with pytest.raises(ValueError, match="states must be non-empty"):
        TemporalConsensusPosition(
            index=0,
            states=(),
            supporting_history_count=1,
            total_history_count=1,
        )


def test_single_history_is_full_consensus() -> None:
    result = analyze_history_consensus((history(),))

    assert result.history_count == 1
    assert result.consensus_position_count == 3
    assert result.disagreement_position_count == 0
    assert result.incomplete_position_count == 0
    assert result.consensus_ratio == 1.0


def test_consensus_preserves_first_seen_state_order() -> None:
    result = analyze_history_consensus(
        (
            history(
                evidence_ids=(1,),
                states=("active",),
            ),
            history(
                evidence_ids=(10,),
                states=("paused",),
            ),
            history(
                evidence_ids=(20,),
                states=("active",),
            ),
        )
    )

    assert result.positions[0].states == ("active", "paused")

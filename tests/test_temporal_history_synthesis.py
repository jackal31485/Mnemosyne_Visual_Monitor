from dataclasses import FrozenInstanceError

import pytest

from src.domain.temporal_history_consensus import (
    analyze_history_consensus,
)
from src.domain.temporal_history_synthesis import (
    TemporalHistorySynthesis,
    synthesize_history,
    synthesize_history_groups,
)
from src.domain.temporal_state_history import TemporalStateHistory


def history(
    states=("draft", "active", "retired"),
    evidence_ids=None,
    *,
    uncertainty=False,
):
    if evidence_ids is None:
        evidence_ids = tuple(range(1, len(states) + 1))

    observation_count = len(states)
    transition_count = max(0, observation_count - 1)

    return TemporalStateHistory(
        subject_type="entity",
        subject_id="alpha",
        evidence_ids=evidence_ids,
        states=states,
        initial_state=states[0] if states else None,
        final_state=states[-1] if states else None,
        observation_count=observation_count,
        transition_count=transition_count,
        changed_transition_count=transition_count,
        unchanged_transition_count=0,
        definite_transition_count=(
            0 if uncertainty else transition_count
        ),
        indeterminate_transition_count=(
            transition_count if uncertainty else 0
        ),
    )


def other_history(subject_id="beta"):
    value = history()
    return TemporalStateHistory(
        subject_type=value.subject_type,
        subject_id=subject_id,
        evidence_ids=value.evidence_ids,
        states=value.states,
        initial_state=value.initial_state,
        final_state=value.final_state,
        observation_count=value.observation_count,
        transition_count=value.transition_count,
        changed_transition_count=value.changed_transition_count,
        unchanged_transition_count=value.unchanged_transition_count,
        definite_transition_count=value.definite_transition_count,
        indeterminate_transition_count=value.indeterminate_transition_count,
    )


def test_all_histories_agree():
    result = synthesize_history(
        [
            history(),
            history(evidence_ids=(10, 11, 12)),
        ]
    )

    assert result.history_count == 2
    assert result.observation_count == 6
    assert result.distinct_state_count == 3
    assert result.initial_states == ("draft", "draft")
    assert result.final_states == ("retired", "retired")
    assert result.consensus_states == ("draft", "active", "retired")
    assert result.divergent_positions == ()
    assert result.incomplete_positions == ()
    assert result.consensus_ratio == 1.0
    assert result.disagreement_ratio == 0.0
    assert result.coverage_ratio == 1.0
    assert result.has_consensus
    assert result.is_stable
    assert result.is_complete
    assert not result.is_uncertain


def test_majority_state_is_not_called_consensus():
    result = synthesize_history(
        [
            history(),
            history(states=("draft", "paused", "retired")),
            history(),
        ]
    )

    assert result.consensus_states == ("draft", "retired")
    assert result.divergent_positions == (1,)
    assert result.has_divergence
    assert not result.is_stable


def test_incomplete_position_is_distinct_from_divergence():
    result = synthesize_history(
        [
            history(),
            history(states=("draft", "active")),
        ]
    )

    assert result.consensus_states == ("draft", "active")
    assert result.divergent_positions == ()
    assert result.incomplete_positions == (2,)
    assert result.has_incomplete_history
    assert result.is_uncertain
    assert not result.is_complete


def test_multiple_divergent_positions_are_sorted():
    result = synthesize_history(
        [
            history(states=("draft", "active", "retired")),
            history(states=("review", "active", "closed")),
        ]
    )

    assert result.divergent_positions == (0, 2)
    assert result.consensus_states == ("active",)


def test_empty_history_can_be_synthesized():
    result = synthesize_history(
        [
            history(states=(), evidence_ids=()),
            history(states=(), evidence_ids=()),
        ]
    )

    assert result.observation_count == 0
    assert result.distinct_state_count == 0
    assert result.initial_states == ()
    assert result.final_states == ()
    assert result.consensus_states == ()
    assert result.coverage_ratio == 0.0
    assert result.is_complete
    assert not result.is_stable


def test_single_history_is_fully_consensual():
    result = synthesize_history([history()])

    assert result.history_count == 1
    assert result.consensus_states == ("draft", "active", "retired")
    assert result.consensus_ratio == 1.0
    assert result.disagreement_ratio == 0.0
    assert result.coverage_ratio == 1.0
    assert result.is_stable


def test_temporal_uncertainty_is_preserved():
    result = synthesize_history(
        [
            history(uncertainty=True),
            history(uncertainty=True),
        ]
    )

    assert result.has_temporal_uncertainty
    assert result.is_uncertain


def test_different_subjects_are_rejected():
    with pytest.raises(ValueError, match="same subject"):
        synthesize_history(
            [
                history(),
                other_history(),
            ]
        )


def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="at least one history"):
        synthesize_history([])


def test_invalid_history_is_rejected():
    with pytest.raises(TypeError, match="TemporalStateHistory"):
        synthesize_history([object()])


def test_result_is_immutable():
    result = synthesize_history([history()])

    with pytest.raises(FrozenInstanceError):
        result.subject_id = "changed"


def test_consensus_input_is_validated():
    with pytest.raises(TypeError, match="TemporalHistoryConsensus"):
        from src.domain.temporal_history_synthesis import _synthesize

        _synthesize((history(),), object())


def test_grouped_synthesis_is_deterministic():
    alpha = history()

    beta_base = history()
    beta = TemporalStateHistory(
        subject_type="entity",
        subject_id="beta",
        evidence_ids=beta_base.evidence_ids,
        states=beta_base.states,
        initial_state=beta_base.initial_state,
        final_state=beta_base.final_state,
        observation_count=beta_base.observation_count,
        transition_count=beta_base.transition_count,
        changed_transition_count=beta_base.changed_transition_count,
        unchanged_transition_count=beta_base.unchanged_transition_count,
        definite_transition_count=beta_base.definite_transition_count,
        indeterminate_transition_count=beta_base.indeterminate_transition_count,
    )

    results = synthesize_history_groups([beta, alpha])

    assert [
        (item.subject_type, item.subject_id)
        for item in results
    ] == [
        ("entity", "alpha"),
        ("entity", "beta"),
    ]


def test_empty_group_returns_empty_tuple():
    assert synthesize_history_groups([]) == ()


def test_consensus_api_matches_synthesis_classification():
    histories = [
        history(),
        history(states=("draft", "paused", "retired")),
    ]

    consensus = analyze_history_consensus(histories)
    synthesis = synthesize_history(histories)

    assert synthesis.consensus_ratio == consensus.consensus_ratio
    assert synthesis.disagreement_ratio == consensus.disagreement_ratio
    assert synthesis.divergent_positions == (1,)


def test_synthesis_result_type():
    result = synthesize_history([history()])

    assert isinstance(result, TemporalHistorySynthesis)

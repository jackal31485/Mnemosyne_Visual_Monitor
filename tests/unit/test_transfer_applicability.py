import pytest

from src.domain.transfer_applicability import (
    ApplicabilityDecision,
    ContradictionSignal,
    TransferApplicabilitySignals,
    analyze_transfer_applicability,
)
from src.domain.transfer_candidate_generation import TransferSource, generate_transfer_candidate
from src.domain.transfer_contract import TransferStatus


def _candidate():
    source = TransferSource(
        knowledge_id="knowledge-1",
        source_profile="horus",
        evidence_ids=("evidence-1",),
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
        entity_ids=("entity-1",),
        relationship_ids=("relationship-1",),
        temporal_scope=("2026-01",),
    )
    return generate_transfer_candidate(source, "thoth")


def _signals(**overrides):
    values = dict(
        evidence_quality=0.9,
        novelty=0.9,
        entity_overlap=0.8,
        relationship_overlap=0.7,
        temporal_compatibility=0.9,
        destination_knowledge_gap=0.9,
    )
    values.update(overrides)
    return TransferApplicabilitySignals(**values)


def test_applicable_analysis_is_deterministic_and_explainable():
    candidate = _candidate()
    analysis = analyze_transfer_applicability(candidate, _signals())

    assert analysis.decision is ApplicabilityDecision.APPLICABLE
    assert analysis.benefit_score == pytest.approx(0.88)
    assert analysis.applicability_score == pytest.approx(0.83)
    assert "destination_knowledge_gap" in analysis.reasons
    assert "sufficient_evidence" in analysis.reasons
    assert analysis.candidate_id == candidate.candidate_id


def test_strong_contradiction_requires_review_without_resolving_conflict():
    analysis = analyze_transfer_applicability(
        _candidate(),
        _signals(contradiction=ContradictionSignal.STRONG),
    )

    assert analysis.decision is ApplicabilityDecision.REVIEW_REQUIRED
    assert "strong_destination_contradiction" in analysis.reasons


def test_weak_or_missing_applicability_is_not_applicable():
    analysis = analyze_transfer_applicability(
        _candidate(),
        _signals(
            entity_overlap=0.0,
            relationship_overlap=0.0,
            temporal_compatibility=0.0,
            destination_knowledge_gap=0.1,
            novelty=0.1,
            evidence_quality=0.1,
        ),
    )

    assert analysis.decision is ApplicabilityDecision.NOT_APPLICABLE


def test_prior_transfer_redundancy_reduces_benefit():
    baseline = analyze_transfer_applicability(_candidate(), _signals())
    redundant = analyze_transfer_applicability(
        _candidate(),
        _signals(prior_transfer_redundancy=1.0),
    )

    assert redundant.benefit_score < baseline.benefit_score
    assert "prior_transfer_redundancy" in redundant.reasons


def test_candidate_is_not_mutated_or_authorized():
    candidate = _candidate()
    before = candidate

    analyze_transfer_applicability(candidate, _signals())

    assert candidate is before
    assert candidate.status is TransferStatus.CANDIDATE


def test_rejected_candidate_cannot_be_analyzed():
    candidate = _candidate().transition_to(TransferStatus.REJECTED)

    with pytest.raises(ValueError, match="rejected or revoked"):
        analyze_transfer_applicability(candidate, _signals())


def test_revoked_candidate_cannot_be_analyzed():
    candidate = _candidate().transition_to(TransferStatus.REVOKED)

    with pytest.raises(ValueError, match="rejected or revoked"):
        analyze_transfer_applicability(candidate, _signals())


@pytest.mark.parametrize(
    "field",
    [
        "evidence_quality",
        "novelty",
        "entity_overlap",
        "relationship_overlap",
        "temporal_compatibility",
        "destination_knowledge_gap",
        "prior_transfer_redundancy",
    ],
)
def test_signal_scores_are_bounded(field):
    values = dict(
        evidence_quality=0.5,
        novelty=0.5,
        entity_overlap=0.5,
        relationship_overlap=0.5,
        temporal_compatibility=0.5,
        destination_knowledge_gap=0.5,
        prior_transfer_redundancy=0.0,
    )

    values[field] = -0.01
    with pytest.raises(ValueError):
        TransferApplicabilitySignals(**values)

    values[field] = 1.01
    with pytest.raises(ValueError):
        TransferApplicabilitySignals(**values)


def test_bool_is_not_accepted_as_numeric_score():
    values = dict(
        evidence_quality=True,
        novelty=0.5,
        entity_overlap=0.5,
        relationship_overlap=0.5,
        temporal_compatibility=0.5,
        destination_knowledge_gap=0.5,
    )

    with pytest.raises(TypeError):
        TransferApplicabilitySignals(**values)


def test_analysis_requires_transfer_candidate():
    with pytest.raises(TypeError, match="TransferCandidate"):
        analyze_transfer_applicability(object(), _signals())


def test_analysis_is_not_authorization_or_adoption():
    analysis = analyze_transfer_applicability(_candidate(), _signals())

    assert analysis.decision is ApplicabilityDecision.APPLICABLE
    assert not hasattr(analysis, "authorization_id")
    assert not hasattr(analysis, "adopted_at")

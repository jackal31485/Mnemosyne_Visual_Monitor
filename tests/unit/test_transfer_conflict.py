"""Phase 14F cross-profile conflict analysis tests."""

from datetime import datetime

import pytest

from src.domain.consolidation_candidate import ConsolidationOutcome

from src.domain.contradiction_handling import (
    ContradictionAnalysisResult,
    ContradictionKind,
    ContradictionOutcome,
    ContradictionPair,
)
from src.domain.transfer_conflict import (
    DestinationKnowledgeState,
    TransferConflictOutcome,
    TransferConflictSignals,
    analyze_transfer_conflict,
)
from src.domain.transfer_contract import (
    TransferCandidate,
    TransferProvenance,
    TransferStatus,
)


NOW = datetime(2026, 9, 18, 16, 0, 0)


def _candidate(**overrides) -> TransferCandidate:
    provenance = TransferProvenance(
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        transfer_candidate_id="candidate-001",
        transfer_record_id="transfer-001",
        evidence_ids=("evidence-001",),
        source_memory_ids=("memory-001",),
        observation_ids=("observation-001",),
        mental_model_id="model-001",
    )

    values = dict(
        candidate_id="candidate-001",
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        proposed_applicability="applicable",
        provenance=provenance,
        supporting_evidence_ids=("evidence-001",),
        source_memory_ids=("memory-001",),
        observation_ids=("observation-001",),
        mental_model_id="model-001",
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
        temporal_scope=("2026-09",),
        benefit_signals=("destination_gap",),
        created_at=NOW,
    )
    values.update(overrides)
    return TransferCandidate(**values)


def _destination(**overrides) -> DestinationKnowledgeState:
    values = dict(
        knowledge_id="destination-001",
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
        evidence_ids=("destination-evidence-001",),
        observation_ids=("destination-observation-001",),
        temporal_scope=("2026-09",),
        source_profiles=("boss",),
    )
    values.update(overrides)
    return DestinationKnowledgeState(**values)


def _contradiction(
    *,
    outcome=ContradictionOutcome.CONFLICT,
    temporal_resolution=None,
):
    pair = ContradictionPair(
        left_evidence_id="evidence-001",
        right_evidence_id="destination-evidence-001",
        kind=ContradictionKind.DIRECT,
        temporal_resolution=temporal_resolution,
        reason="explicit incompatible assertions",
    )

    return ContradictionAnalysisResult(
        candidate_id="candidate-001",
        contradiction_pairs=(pair,),
        contradictory_evidence_ids=(
            "destination-evidence-001",
            "evidence-001",
        ),
        contradictory_profiles=("boss", "jeeves"),
        kind=(
            ContradictionKind.TEMPORAL
            if temporal_resolution is True
            else ContradictionKind.DIRECT
        ),
        outcome=outcome,
        proposed_consolidation_outcome=ConsolidationOutcome.CONFLICT,
        temporal_resolution_explicit=temporal_resolution is True,
        requires_review=outcome is not ContradictionOutcome.TEMPORALLY_SEPARATE,
        preservation_required=True,
        weighting_was_not_used_to_suppress_conflict=True,
        reasons=("contradictory_evidence_preserved",),
    )


def test_no_destination_knowledge_means_no_conflict():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=None,
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.NO_CONFLICT
    assert result.record.destination_knowledge_id is None


def test_entity_mismatch_means_no_conflict():
    destination = _destination(
        entity_ids=("entity-postgresql",),
        relationship_ids=("relationship-default",),
    )

    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=destination,
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.NO_CONFLICT


def test_compatible_destination_knowledge_can_coexist():
    destination = _destination(
        relationship_ids=("relationship-secondary",),
    )

    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=destination,
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.ADOPT_ALONGSIDE


def test_equivalent_destination_knowledge_keeps_existing_when_no_contradiction():
    destination = _destination(
        evidence_ids=("evidence-001",),
        observation_ids=("observation-001",),
    )

    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=destination,
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.KEEP_EXISTING


def test_temporally_resolved_contradiction_is_preserved_as_separate():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=_contradiction(
            outcome=ContradictionOutcome.TEMPORALLY_SEPARATE,
            temporal_resolution=True,
        ),
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.TEMPORALLY_SEPARATE
    assert "evidence-001" in result.record.contradictory_evidence_ids
    assert "destination-evidence-001" in result.record.contradictory_evidence_ids


def test_unknown_temporal_resolution_requires_review():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=_contradiction(
            outcome=ContradictionOutcome.REVIEW_REQUIRED,
            temporal_resolution=None,
        ),
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.REVIEW_REQUIRED
    assert result.requires_review is True


def test_unresolved_contradiction_is_conflict():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=_contradiction(
            outcome=ContradictionOutcome.CONFLICT,
            temporal_resolution=False,
        ),
        analyzed_at=NOW,
    )

    assert result.outcome is TransferConflictOutcome.CONFLICT
    assert result.record.signals.destination_match is True


def test_source_profile_identity_does_not_determine_outcome():
    first = analyze_transfer_conflict(
        _candidate(source_profile="jeeves"),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    other_provenance = TransferProvenance(
        source_profile="hawk",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        transfer_candidate_id="candidate-001",
        transfer_record_id="transfer-001",
        evidence_ids=("evidence-001",),
        source_memory_ids=("memory-001",),
        observation_ids=("observation-001",),
        mental_model_id="model-001",
    )

    second = analyze_transfer_conflict(
        _candidate(
            source_profile="hawk",
            provenance=other_provenance,
        ),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert first.outcome is second.outcome


def test_conflict_identity_is_deterministic():
    first = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )
    second = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert first.record.conflict_id == second.record.conflict_id
    assert first.record == second.record


def test_source_and_destination_provenance_are_preserved():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    record = result.record

    assert record.source_profile == "jeeves"
    assert record.destination_profile == "boss"
    assert record.source_knowledge_id == "knowledge-001"
    assert record.destination_knowledge_id == "destination-001"
    assert record.source_memory_ids == ("memory-001",)
    assert record.source_observation_ids == ("observation-001",)
    assert record.destination_observation_ids == (
        "destination-observation-001",
    )


def test_temporal_scope_is_preserved():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert result.record.source_temporal_scope == ("2026-09",)
    assert result.record.destination_temporal_scope == ("2026-09",)


def test_raw_memory_content_is_not_part_of_contract():
    state = _destination()

    assert not hasattr(state, "content")
    assert not hasattr(state, "raw_memory")
    assert not hasattr(state, "description")

    signals = TransferConflictSignals(
        evidence_overlap=0.5,
        entity_overlap=0.5,
        relationship_overlap=0.5,
        temporal_compatibility=1.0,
        provenance_compatible=True,
        destination_match=True,
    )

    assert not hasattr(signals, "content")


def test_conflict_record_is_immutable():
    result = analyze_transfer_conflict(
        _candidate(),
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    with pytest.raises((AttributeError, TypeError)):
        result.record.outcome = TransferConflictOutcome.CONFLICT


def test_invalid_candidate_type_is_rejected():
    with pytest.raises(TypeError, match="TransferCandidate"):
        analyze_transfer_conflict(
            object(),
            transfer_id="transfer-001",
            destination=None,
            contradiction_analysis=None,
            analyzed_at=NOW,
        )


def test_mismatched_contradiction_analysis_is_rejected():
    analysis = _contradiction()
    analysis = ContradictionAnalysisResult(
        candidate_id="different-candidate",
        contradiction_pairs=analysis.contradiction_pairs,
        contradictory_evidence_ids=analysis.contradictory_evidence_ids,
        contradictory_profiles=analysis.contradictory_profiles,
        kind=analysis.kind,
        outcome=analysis.outcome,
        proposed_consolidation_outcome=analysis.proposed_consolidation_outcome,
        temporal_resolution_explicit=analysis.temporal_resolution_explicit,
        requires_review=analysis.requires_review,
        preservation_required=analysis.preservation_required,
        weighting_was_not_used_to_suppress_conflict=(
            analysis.weighting_was_not_used_to_suppress_conflict
        ),
        reasons=analysis.reasons,
    )

    with pytest.raises(ValueError, match="does not match"):
        analyze_transfer_conflict(
            _candidate(),
            transfer_id="transfer-001",
            destination=_destination(),
            contradiction_analysis=analysis,
            analyzed_at=NOW,
        )


def test_conflict_analysis_does_not_change_candidate():
    candidate = _candidate()

    analyze_transfer_conflict(
        candidate,
        transfer_id="transfer-001",
        destination=_destination(),
        contradiction_analysis=None,
        analyzed_at=NOW,
    )

    assert candidate.status is TransferStatus.CANDIDATE
    assert candidate.source_profile == "jeeves"
    assert candidate.destination_profile == "boss"

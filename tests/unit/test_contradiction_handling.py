from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)
from src.domain.contradiction_handling import (
    ContradictionAnalysisResult,
    ContradictionHandler,
    ContradictionKind,
    ContradictionOutcome,
    ContradictionPair,
    ContradictionPolicy,
)
from src.domain.evidence_validation import (
    EvidenceLifecycleState,
    EvidenceReference,
    EvidenceValidationPolicy,
    EvidenceValidationResult,
    EvidenceValidationOutcome,
)
from src.domain.evidence_weighting import (
    EvidenceWeightReference,
    EvidenceWeightingPolicy,
    EvidenceWeightingResult,
    EvidenceWeightResult,
    EvidenceWeightingStatus,
)
from src.domain.observation_similarity import (
    ObservationReference,
    ObservationSimilarityResult,
    ObservationSimilaritySignals,
)


def _similarity_result(
    left_id: str = "obs-1",
    right_id: str = "obs-2",
) -> ObservationSimilarityResult:
    left = ObservationReference(
        observation_id=left_id,
        source_profile="athena",
        source_memory_id=f"memory-{left_id}",
    )
    right = ObservationReference(
        observation_id=right_id,
        source_profile="athena",
        source_memory_id=f"memory-{right_id}",
    )
    signals = ObservationSimilaritySignals(
        normalized_text=1.0,
        semantic=1.0,
        shared_entities=1.0,
        shared_relationships=1.0,
        temporal_compatibility=1.0,
        shared_evidence=1.0,
        profile_overlap=1.0,
        explicit_identifier=1.0,
        observation_type=1.0,
        confidence=1.0,
        provenance=1.0,
    )
    return ObservationSimilarityResult(
        left=left,
        right=right,
        signals=signals,
        similarity_score=1.0,
        is_candidate=True,
        reasons=frozenset({"test similarity"}),
    )


def _candidate(
    evidence_ids: tuple[str, ...] = ("e-1", "e-2"),
) -> ConsolidationCandidate:
    similarity = _similarity_result()

    return ConsolidationCandidate(
        candidate_id="candidate-1",
        observations=(similarity.left, similarity.right),
        similarity_result=similarity,
        reasons=frozenset({"near duplicate"}),
        entity_ids=("entity-1",),
        relationship_ids=("relationship-1",),
        temporal_compatibility=True,
        supporting_evidence_ids=evidence_ids,
        contradictory_evidence_ids=(),
        source_profiles=("athena",),
        confidence=1.0,
        proposed_outcome=ConsolidationOutcome.CANDIDATE,
        provenance_complete=True,
    )

def _evidence(
    evidence_id: str,
    profile: str = "athena",
    *,
    lifecycle: EvidenceLifecycleState = EvidenceLifecycleState.PROMOTED,
    temporal_compatible: bool | None = True,
    provenance_complete: bool = True,
) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_profile=profile,
        source_memory_id=f"memory-{evidence_id}",
        lifecycle_state=lifecycle,
        source_memory_exists=True,
        source_profile_authorized=True,
        provenance_complete=provenance_complete,
        temporal_compatible=temporal_compatible,
    )


def _validation(
    candidate: ConsolidationCandidate,
    evidence: tuple[EvidenceReference, ...],
    *,
    invalid: tuple[str, ...] = (),
    contradictory: tuple[str, ...] = (),
) -> EvidenceValidationResult:
    return EvidenceValidationResult(
        candidate_id=candidate.candidate_id,
        evidence=evidence,
        valid_evidence_ids=tuple(
            item.evidence_id
            for item in evidence
            if item.evidence_id not in invalid
        ),
        invalid_evidence_ids=invalid,
        reasons=frozenset({"test validation"}),
        contradictory_evidence_ids=contradictory,
        temporal_incompatibility=False,
        provenance_complete=True,
        all_support_current=not invalid,
        outcome=(
            EvidenceValidationOutcome.CONFLICT
            if contradictory
            else (
                EvidenceValidationOutcome.REJECTED
                if invalid
                else EvidenceValidationOutcome.ELIGIBLE
            )
        ),
        proposed_consolidation_outcome=(
            ConsolidationOutcome.CONFLICT
            if contradictory
            else ConsolidationOutcome.CANDIDATE
        ),
    )


def _weighting(
    candidate: ConsolidationCandidate,
    evidence: tuple[EvidenceReference, ...],
    *,
    revoked: bool = False,
) -> EvidenceWeightingResult:
    results = tuple(
        EvidenceWeightResult(
            evidence_id=item.evidence_id,
            source_profile=item.source_profile,
            status=(
                EvidenceWeightingStatus.HISTORICAL
                if revoked
                else EvidenceWeightingStatus.CURRENT
            ),
            confidence=0.8,
            precision=0.8,
            reliability=0.8,
            recency=0.8,
            corroboration=0.5,
            independence=0.5,
            provenance=1.0,
            composite_weight=0.7 if not revoked else 0.0,
            unavailable_signals=frozenset(),
            reasons=frozenset({"test weight"}),
        )
        for item in evidence
    )

    return EvidenceWeightingResult(
        candidate_id=candidate.candidate_id,
        evidence=results,
        ranked_evidence_ids=tuple(
            sorted(item.evidence_id for item in evidence)
        ),
        total_current_weight=min(
            sum(
                item.composite_weight
                for item in results
                if item.status == EvidenceWeightingStatus.CURRENT
            ),
            1.0,
        ),
        current_support_count=sum(
            item.status == EvidenceWeightingStatus.CURRENT
            for item in results
        ),
        independent_profile_count=len(
            {item.source_profile for item in evidence}
        ),
        contradiction_present=False,
        recalculation_required=revoked,
    )


def _handler_inputs(
    *,
    profiles: tuple[str, str] = ("athena", "athena"),
    temporal_resolution: bool | None = False,
    kind: ContradictionKind = ContradictionKind.DIRECT,
):
    candidate = _candidate()
    evidence = (
        _evidence("e-1", profiles[0]),
        _evidence("e-2", profiles[1]),
    )
    validation = _validation(candidate, evidence)
    weighting = _weighting(candidate, evidence)
    pair = ContradictionPair(
        left_evidence_id="e-1",
        right_evidence_id="e-2",
        kind=kind,
        temporal_resolution=temporal_resolution,
        reason="conflicting values",
    )
    return candidate, validation, weighting, pair


def test_pair_requires_distinct_evidence_ids():
    with pytest.raises(ValueError):
        ContradictionPair("e-1", "e-1")


def test_pair_rejects_invalid_kind():
    with pytest.raises(TypeError):
        ContradictionPair(
            "e-1",
            "e-2",
            kind="direct",
        )


def test_pair_rejects_non_text_reason():
    with pytest.raises(TypeError):
        ContradictionPair(
            "e-1",
            "e-2",
            reason=None,
        )


def test_pair_ids_are_deterministic():
    pair = ContradictionPair("e-9", "e-2")
    assert pair.evidence_ids == ("e-2", "e-9")


def test_policy_defaults_preserve_conflict():
    policy = ContradictionPolicy()
    assert policy.preserve_all_contradictory_evidence is True
    assert policy.require_explicit_temporal_resolution is True
    assert policy.independent_profiles_require_conflict is True
    assert policy.unknown_temporal_state_requires_review is True
    assert policy.weighting_cannot_resolve_contradiction is True


@pytest.mark.parametrize(
    "field",
    (
        "preserve_all_contradictory_evidence",
        "require_explicit_temporal_resolution",
        "independent_profiles_require_conflict",
        "unknown_temporal_state_requires_review",
        "weighting_cannot_resolve_contradiction",
    ),
)
def test_policy_rejects_non_boolean_values(field):
    with pytest.raises(TypeError):
        ContradictionPolicy(**{field: "yes"})


def test_no_contradiction_is_not_conflict():
    candidate = _candidate()
    evidence = (_evidence("e-1"), _evidence("e-2"))
    validation = _validation(candidate, evidence)
    weighting = _weighting(candidate, evidence)

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(),
    )

    assert result.kind == ContradictionKind.NONE
    assert result.outcome == ContradictionOutcome.NO_CONTRADICTION
    assert result.proposed_consolidation_outcome == ConsolidationOutcome.CANDIDATE
    assert result.requires_review is False
    assert result.preservation_required is False
    assert result.contradictory_evidence_ids == ()


def test_direct_contradiction_becomes_conflict():
    candidate, validation, weighting, pair = _handler_inputs()

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.kind == ContradictionKind.DIRECT
    assert result.outcome == ContradictionOutcome.CONFLICT
    assert result.proposed_consolidation_outcome == ConsolidationOutcome.CONFLICT
    assert result.requires_review is True
    assert result.preservation_required is True
    assert result.contradictory_evidence_ids == ("e-1", "e-2")


def test_contradiction_from_independent_profiles_is_preserved():
    candidate, validation, weighting, pair = _handler_inputs(
        profiles=("athena", "horus"),
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.contradictory_profiles == ("athena", "horus")
    assert "contradictory_evidence_from_independent_profiles" in result.reasons
    assert result.outcome == ContradictionOutcome.CONFLICT


def test_explicit_temporal_resolution_preserves_temporal_states():
    candidate, validation, weighting, pair = _handler_inputs(
        temporal_resolution=True,
        kind=ContradictionKind.TEMPORAL,
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.kind == ContradictionKind.TEMPORAL
    assert result.outcome == ContradictionOutcome.TEMPORALLY_SEPARATE
    assert result.proposed_consolidation_outcome == ConsolidationOutcome.KEEP_SEPARATE
    assert result.temporal_resolution_explicit is True
    assert result.is_temporally_resolved is True
    assert result.requires_review is False
    assert result.preservation_required is True


def test_unknown_temporal_resolution_requires_review():
    candidate, validation, weighting, pair = _handler_inputs(
        temporal_resolution=None,
        kind=ContradictionKind.TEMPORAL,
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.outcome == ContradictionOutcome.REVIEW_REQUIRED
    assert result.proposed_consolidation_outcome == ConsolidationOutcome.REVIEW_REQUIRED
    assert result.requires_review is True
    assert result.temporal_resolution_explicit is False
    assert "temporal_resolution_unknown" in result.reasons
    assert "temporal_bounds_not_invented" in result.reasons


def test_explicit_temporal_non_resolution_remains_conflict():
    candidate, validation, weighting, pair = _handler_inputs(
        temporal_resolution=False,
        kind=ContradictionKind.TEMPORAL,
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.outcome == ContradictionOutcome.CONFLICT
    assert result.requires_review is True
    assert "temporal_evidence_does_not_resolve_contradiction" in result.reasons


def test_stronger_weight_does_not_suppress_contradiction():
    candidate, validation, weighting, pair = _handler_inputs()

    stronger_weighting = EvidenceWeightingResult(
        candidate_id=weighting.candidate_id,
        evidence=tuple(
            EvidenceWeightResult(
                evidence_id=item.evidence_id,
                source_profile=item.source_profile,
                status=item.status,
                confidence=item.confidence,
                precision=item.precision,
                reliability=item.reliability,
                recency=item.recency,
                corroboration=item.corroboration,
                independence=item.independence,
                provenance=item.provenance,
                composite_weight=(
                    0.99 if item.evidence_id == "e-1" else 0.01
                ),
                unavailable_signals=item.unavailable_signals,
                reasons=item.reasons,
            )
            for item in weighting.evidence
        ),
        ranked_evidence_ids=("e-1", "e-2"),
        total_current_weight=1.0,
        current_support_count=2,
        independent_profile_count=1,
        contradiction_present=False,
        recalculation_required=False,
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=stronger_weighting,
        contradiction_pairs=(pair,),
    )

    assert result.outcome == ContradictionOutcome.CONFLICT
    assert result.contradictory_evidence_ids == ("e-1", "e-2")
    assert result.weighting_was_not_used_to_suppress_conflict is True
    assert "evidence_weighting_cannot_suppress_contradiction" in result.reasons


def test_multiple_pairs_are_sorted_and_preserved():
    candidate = _candidate(
        evidence_ids=("e-1", "e-2", "e-3", "e-4"),
    )
    evidence = tuple(
        _evidence(evidence_id)
        for evidence_id in ("e-1", "e-2", "e-3", "e-4")
    )
    validation = _validation(candidate, evidence)
    weighting = _weighting(candidate, evidence)

    pairs = (
        ContradictionPair("e-4", "e-3"),
        ContradictionPair("e-2", "e-1"),
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=pairs,
    )

    assert [pair.evidence_ids for pair in result.contradiction_pairs] == [
        ("e-1", "e-2"),
        ("e-3", "e-4"),
    ]
    assert result.contradictory_evidence_ids == (
        "e-1",
        "e-2",
        "e-3",
        "e-4",
    )


def test_duplicate_contradiction_pair_is_rejected():
    candidate, validation, weighting, pair = _handler_inputs()

    with pytest.raises(ValueError):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=validation,
            weighting=weighting,
            contradiction_pairs=(pair, pair),
        )


def test_contradiction_evidence_must_belong_to_candidate():
    candidate, validation, weighting, _ = _handler_inputs()

    pair = ContradictionPair("e-1", "e-999")

    with pytest.raises(ValueError, match="not present in candidate"):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=validation,
            weighting=weighting,
            contradiction_pairs=(pair,),
        )


def test_validation_candidate_id_must_match():
    candidate, validation, weighting, pair = _handler_inputs()

    mismatched = EvidenceValidationResult(
        candidate_id="other-candidate",
        evidence=validation.evidence,
        valid_evidence_ids=validation.valid_evidence_ids,
        invalid_evidence_ids=validation.invalid_evidence_ids,
        reasons=validation.reasons,
        contradictory_evidence_ids=validation.contradictory_evidence_ids,
        temporal_incompatibility=validation.temporal_incompatibility,
        provenance_complete=validation.provenance_complete,
        all_support_current=validation.all_support_current,
        outcome=validation.outcome,
        proposed_consolidation_outcome=validation.proposed_consolidation_outcome,
    )

    with pytest.raises(ValueError, match="validation result"):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=mismatched,
            weighting=weighting,
            contradiction_pairs=(pair,),
        )


def test_weighting_candidate_id_must_match():
    candidate, validation, weighting, pair = _handler_inputs()

    mismatched = EvidenceWeightingResult(
        candidate_id="other-candidate",
        evidence=weighting.evidence,
        ranked_evidence_ids=weighting.ranked_evidence_ids,
        total_current_weight=weighting.total_current_weight,
        current_support_count=weighting.current_support_count,
        independent_profile_count=weighting.independent_profile_count,
        contradiction_present=weighting.contradiction_present,
        recalculation_required=weighting.recalculation_required,
    )

    with pytest.raises(ValueError, match="weighting result"):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=validation,
            weighting=mismatched,
            contradiction_pairs=(pair,),
        )


def test_candidate_validation_and_weighting_evidence_sets_must_align():
    candidate, validation, weighting, pair = _handler_inputs()

    extra = _evidence("e-extra")

    mismatched_validation = _validation(
        candidate,
        validation.evidence + (extra,),
    )

    with pytest.raises(ValueError, match="exactly match"):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=mismatched_validation,
            weighting=weighting,
            contradiction_pairs=(pair,),
        )


def test_non_candidate_argument_is_rejected():
    _, validation, weighting, pair = _handler_inputs()

    with pytest.raises(TypeError):
        ContradictionHandler().analyze(
            candidate="candidate",
            validation=validation,
            weighting=weighting,
            contradiction_pairs=(pair,),
        )


def test_non_validation_argument_is_rejected():
    candidate, _, weighting, pair = _handler_inputs()

    with pytest.raises(TypeError):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation="validation",
            weighting=weighting,
            contradiction_pairs=(pair,),
        )


def test_non_weighting_argument_is_rejected():
    candidate, validation, _, pair = _handler_inputs()

    with pytest.raises(TypeError):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=validation,
            weighting="weighting",
            contradiction_pairs=(pair,),
        )


def test_non_pair_items_are_rejected():
    candidate, validation, weighting, _ = _handler_inputs()

    with pytest.raises(TypeError):
        ContradictionHandler().analyze(
            candidate=candidate,
            validation=validation,
            weighting=weighting,
            contradiction_pairs=("e-1/e-2",),
        )


def test_result_is_immutable():
    result = ContradictionAnalysisResult(
        candidate_id="candidate-1",
        contradiction_pairs=(),
        contradictory_evidence_ids=(),
        contradictory_profiles=(),
        kind=ContradictionKind.NONE,
        outcome=ContradictionOutcome.NO_CONTRADICTION,
        proposed_consolidation_outcome=ConsolidationOutcome.CANDIDATE,
        temporal_resolution_explicit=False,
        requires_review=False,
        preservation_required=False,
        weighting_was_not_used_to_suppress_conflict=True,
        reasons=("none",),
    )

    with pytest.raises(FrozenInstanceError):
        result.outcome = ContradictionOutcome.CONFLICT


def test_no_input_objects_are_mutated():
    candidate, validation, weighting, pair = _handler_inputs()

    candidate_before = candidate
    validation_before = validation
    weighting_before = weighting

    ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert candidate is candidate_before
    assert validation is validation_before
    assert weighting is weighting_before
    assert candidate.contradictory_evidence_ids == ()
    assert validation.contradictory_evidence_ids == ()


def test_policy_can_require_conflict_for_independent_profiles():
    policy = ContradictionPolicy(
        independent_profiles_require_conflict=True,
    )
    candidate, validation, weighting, pair = _handler_inputs(
        profiles=("athena", "horus"),
    )

    result = ContradictionHandler(policy).analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.outcome == ContradictionOutcome.CONFLICT


def test_result_properties():
    candidate, validation, weighting, pair = _handler_inputs()

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.has_contradiction is True
    assert result.is_conflict is True
    assert result.is_temporally_resolved is False


def test_temporally_resolved_result_properties():
    candidate, validation, weighting, pair = _handler_inputs(
        temporal_resolution=True,
        kind=ContradictionKind.TEMPORAL,
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.has_contradiction is True
    assert result.is_temporally_resolved is True
    assert result.is_conflict is False


def test_preservation_is_required_even_when_temporally_resolved():
    candidate, validation, weighting, pair = _handler_inputs(
        temporal_resolution=True,
        kind=ContradictionKind.TEMPORAL,
    )

    result = ContradictionHandler().analyze(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction_pairs=(pair,),
    )

    assert result.preservation_required is True
    assert result.contradictory_evidence_ids == ("e-1", "e-2")


def test_result_rejects_unpreserved_pair_evidence():
    with pytest.raises(ValueError):
        ContradictionAnalysisResult(
            candidate_id="candidate-1",
            contradiction_pairs=(
                ContradictionPair("e-1", "e-2"),
            ),
            contradictory_evidence_ids=("e-1",),
            contradictory_profiles=("athena",),
            kind=ContradictionKind.DIRECT,
            outcome=ContradictionOutcome.CONFLICT,
            proposed_consolidation_outcome=ConsolidationOutcome.CONFLICT,
            temporal_resolution_explicit=False,
            requires_review=True,
            preservation_required=True,
            weighting_was_not_used_to_suppress_conflict=True,
            reasons=("conflict",),
        )

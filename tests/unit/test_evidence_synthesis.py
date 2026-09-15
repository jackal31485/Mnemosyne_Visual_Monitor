from dataclasses import FrozenInstanceError

import pytest

from src.domain.consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)
from src.domain.contradiction_handling import (
    ContradictionAnalysisResult,
    ContradictionKind,
    ContradictionOutcome,
)
from src.domain.evidence_synthesis import (
    EvidencePreservingSynthesizer,
    SynthesisOutcome,
    SynthesizedMemory,
)
from src.domain.evidence_validation import (
    EvidenceLifecycleState,
    EvidenceReference,
    EvidenceValidationOutcome,
    EvidenceValidationResult,
)
from src.domain.evidence_weighting import (
    EvidenceWeightResult,
    EvidenceWeightingResult,
    EvidenceWeightingStatus,
)
from src.domain.observation_similarity import (
    ObservationReference,
    ObservationSimilarityResult,
    ObservationSimilaritySignals,
)


def _candidate(
    *,
    supporting=("e-1", "e-2"),
    contradictory=(),
):
    left = ObservationReference(
        observation_id="obs-1",
        source_profile="odin",
        source_memory_id="mem-1",
        evidence_id="e-1",
    )
    right = ObservationReference(
        observation_id="obs-2",
        source_profile="thoth",
        source_memory_id="mem-2",
        evidence_id="e-2",
    )

    similarity = ObservationSimilarityResult(
        left=left,
        right=right,
        signals=ObservationSimilaritySignals(
            normalized_text=1.0,
            semantic=1.0,
        ),
        similarity_score=1.0,
        is_candidate=True,
        reasons=frozenset({"near duplicate"}),
    )

    return ConsolidationCandidate(
        candidate_id="candidate-1",
        observations=(left, right),
        similarity_result=similarity,
        reasons=frozenset({"near duplicate"}),
        entity_ids=(),
        relationship_ids=(),
        temporal_compatibility=1.0,
        supporting_evidence_ids=tuple(supporting),
        contradictory_evidence_ids=tuple(contradictory),
        source_profiles=("odin", "thoth"),
        confidence=0.9,
        proposed_outcome=ConsolidationOutcome.CONSOLIDATE,
        provenance_complete=True,
    )


def _validation(candidate, *, revoked=False):
    refs = tuple(
        EvidenceReference(
            evidence_id=evidence_id,
            source_profile=(
                "odin" if evidence_id == "e-1" else "thoth"
            ),
            source_memory_id=f"mem-{evidence_id[-1]}",
            lifecycle_state=(
                EvidenceLifecycleState.REVOKED
                if revoked and evidence_id == "e-2"
                else EvidenceLifecycleState.PROMOTED
            ),
            source_memory_exists=True,
            source_profile_authorized=True,
            provenance_complete=True,
            temporal_compatible=True,
        )
        for evidence_id in (
            *candidate.supporting_evidence_ids,
            *candidate.contradictory_evidence_ids,
        )
    )

    valid = tuple(
        ref.evidence_id
        for ref in refs
        if ref.lifecycle_state == EvidenceLifecycleState.PROMOTED
    )
    invalid = tuple(
        ref.evidence_id
        for ref in refs
        if ref.lifecycle_state != EvidenceLifecycleState.PROMOTED
    )

    return EvidenceValidationResult(
        candidate_id=candidate.candidate_id,
        evidence=refs,
        valid_evidence_ids=valid,
        invalid_evidence_ids=invalid,
        reasons=frozenset(),
        contradictory_evidence_ids=tuple(candidate.contradictory_evidence_ids),
        temporal_incompatibility=False,
        provenance_complete=True,
        all_support_current=not revoked,
        outcome=(
            EvidenceValidationOutcome.ELIGIBLE
            if not revoked
            else EvidenceValidationOutcome.REJECTED
        ),
        proposed_consolidation_outcome=(
            ConsolidationOutcome.CANDIDATE
            if not revoked
            else ConsolidationOutcome.REVIEW_REQUIRED
        ),
    )


def _weighting(candidate, *, revoked=False):
    results = tuple(
        EvidenceWeightResult(
            evidence_id=evidence_id,
            source_profile=(
                "odin" if evidence_id == "e-1" else "thoth"
            ),
            status=(
                EvidenceWeightingStatus.HISTORICAL
                if revoked and evidence_id == "e-2"
                else EvidenceWeightingStatus.CURRENT
            ),
            confidence=0.9,
            precision=0.9,
            reliability=0.9,
            recency=0.9,
            corroboration=0.9,
            independence=0.9,
            provenance=1.0,
            composite_weight=0.7 if not revoked or evidence_id == "e-1" else 0.0,
            unavailable_signals=frozenset(),
            reasons=frozenset(),
        )
        for evidence_id in (
            *candidate.supporting_evidence_ids,
            *candidate.contradictory_evidence_ids,
        )
    )

    return EvidenceWeightingResult(
        candidate_id=candidate.candidate_id,
        evidence=results,
        ranked_evidence_ids=tuple(
            result.evidence_id for result in results
        ),
        total_current_weight=min(
            sum(
                result.composite_weight
                for result in results
                if result.status == EvidenceWeightingStatus.CURRENT
            ),
            1.0,
        ),
        current_support_count=sum(
            result.status == EvidenceWeightingStatus.CURRENT
            for result in results
        ),
        independent_profile_count=2,
        contradiction_present=bool(candidate.contradictory_evidence_ids),
        recalculation_required=revoked,
    )


def _contradiction(
    candidate,
    *,
    outcome=ContradictionOutcome.NO_CONTRADICTION,
    kind=ContradictionKind.NONE,
):
    return ContradictionAnalysisResult(
        candidate_id=candidate.candidate_id,
        contradiction_pairs=(),
        contradictory_evidence_ids=(
            tuple(candidate.contradictory_evidence_ids)
            if candidate.contradictory_evidence_ids
            else (
                ("e-1", "e-2")
                if outcome
                in {
                    ContradictionOutcome.CONFLICT,
                    ContradictionOutcome.REVIEW_REQUIRED,
                    ContradictionOutcome.TEMPORALLY_SEPARATE,
                }
                else ()
            )
        ),
        contradictory_profiles=(),
        kind=kind,
        outcome=outcome,
        proposed_consolidation_outcome=(
            ConsolidationOutcome.CANDIDATE
            if outcome == ContradictionOutcome.NO_CONTRADICTION
            else (
                ConsolidationOutcome.CONFLICT
                if outcome == ContradictionOutcome.CONFLICT
                else ConsolidationOutcome.REVIEW_REQUIRED
            )
        ),
        temporal_resolution_explicit=(
            outcome == ContradictionOutcome.TEMPORALLY_SEPARATE
        ),
        requires_review=(
            outcome == ContradictionOutcome.REVIEW_REQUIRED
        ),
        preservation_required=(
            outcome != ContradictionOutcome.NO_CONTRADICTION
        ),
        weighting_was_not_used_to_suppress_conflict=True,
        reasons=(),
    )


def _synthesize(
    *,
    candidate=None,
    validation=None,
    weighting=None,
    contradiction=None,
    content="Consolidated memory",
    temporal_context=(),
):
    candidate = candidate or _candidate()
    validation = validation or _validation(candidate)
    weighting = weighting or _weighting(candidate)
    contradiction = contradiction or _contradiction(candidate)

    return EvidencePreservingSynthesizer().synthesize(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction=contradiction,
        content=content,
        temporal_context=temporal_context,
    )


def test_synthesizes_valid_candidate():
    result = _synthesize()

    assert isinstance(result, SynthesizedMemory)
    assert result.outcome == SynthesisOutcome.SYNTHESIZED
    assert result.content == "Consolidated memory"
    assert result.candidate_id == "candidate-1"


def test_preserves_supporting_evidence():
    result = _synthesize()

    assert result.supporting_evidence_ids == ("e-1", "e-2")
    assert set(result.supporting_evidence_ids) == {"e-1", "e-2"}


def test_preserves_contradictory_evidence():
    candidate = _candidate(
        supporting=("e-1",),
        contradictory=("e-2",),
    )

    result = _synthesize(
        candidate=candidate,
        validation=_validation(candidate),
        weighting=_weighting(candidate),
        contradiction=_contradiction(
            candidate,
            outcome=ContradictionOutcome.CONFLICT,
            kind=ContradictionKind.DIRECT,
        ),
    )

    assert result.contradictory_evidence_ids == ("e-2",)
    assert result.outcome == SynthesisOutcome.CONFLICT


def test_preserves_source_profiles():
    result = _synthesize()

    assert result.source_profiles == ("odin", "thoth")


def test_preserves_temporal_context():
    result = _synthesize(
        temporal_context=(
            "observed:2026-09-01",
            "updated:2026-09-13",
        )
    )

    assert result.temporal_context == (
        "observed:2026-09-01",
        "updated:2026-09-13",
    )


def test_preserves_provenance_status():
    result = _synthesize()

    assert result.provenance_complete is True


def test_current_evidence_is_distinguished_from_historical_evidence():
    candidate = _candidate()
    validation = _validation(candidate, revoked=True)
    weighting = _weighting(candidate, revoked=True)

    result = _synthesize(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction=_contradiction(candidate),
    )

    assert result.current_evidence_ids == ("e-1",)
    assert result.historical_evidence_ids == ("e-2",)


def test_revoked_evidence_does_not_contribute_current_confidence():
    candidate = _candidate()
    validation = _validation(candidate, revoked=True)
    weighting = _weighting(candidate, revoked=True)

    result = _synthesize(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction=_contradiction(candidate),
    )

    assert result.confidence == 0.0
    assert result.outcome == SynthesisOutcome.INVALIDATED


def test_conflict_prevents_synthesis():
    candidate = _candidate()
    contradiction = _contradiction(
        candidate,
        outcome=ContradictionOutcome.CONFLICT,
        kind=ContradictionKind.DIRECT,
    )

    result = _synthesize(
        candidate=candidate,
        validation=_validation(candidate),
        weighting=_weighting(candidate),
        contradiction=contradiction,
    )

    assert result.outcome == SynthesisOutcome.CONFLICT
    assert result.confidence == 0.0


def test_review_required_prevents_synthesis():
    candidate = _candidate()
    contradiction = _contradiction(
        candidate,
        outcome=ContradictionOutcome.REVIEW_REQUIRED,
        kind=ContradictionKind.TEMPORAL,
    )

    result = _synthesize(
        candidate=candidate,
        validation=_validation(candidate),
        weighting=_weighting(candidate),
        contradiction=contradiction,
    )

    assert result.outcome == SynthesisOutcome.REVIEW_REQUIRED
    assert result.confidence == 0.0


def test_temporal_separation_keeps_evidence_without_merging():
    candidate = _candidate()

    contradiction = _contradiction(
        candidate,
        outcome=ContradictionOutcome.TEMPORALLY_SEPARATE,
        kind=ContradictionKind.TEMPORAL,
    )

    result = _synthesize(
        candidate=candidate,
        validation=_validation(candidate),
        weighting=_weighting(candidate),
        contradiction=contradiction,
    )

    assert result.outcome == SynthesisOutcome.KEEP_SEPARATE
    assert result.supporting_evidence_ids == ("e-1", "e-2")


def test_empty_content_is_rejected():
    with pytest.raises(ValueError):
        _synthesize(content="   ")


def test_candidate_validation_id_mismatch_is_rejected():
    candidate = _candidate()
    validation = _validation(candidate)

    invalid = EvidenceValidationResult(
        candidate_id="different",
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

    with pytest.raises(ValueError):
        _synthesize(
            candidate=candidate,
            validation=invalid,
            weighting=_weighting(candidate),
            contradiction=_contradiction(candidate),
        )


def test_candidate_weighting_id_mismatch_is_rejected():
    candidate = _candidate()
    weighting = _weighting(candidate)

    invalid = EvidenceWeightingResult(
        candidate_id="different",
        evidence=weighting.evidence,
        ranked_evidence_ids=weighting.ranked_evidence_ids,
        total_current_weight=weighting.total_current_weight,
        current_support_count=weighting.current_support_count,
        independent_profile_count=weighting.independent_profile_count,
        contradiction_present=weighting.contradiction_present,
        recalculation_required=weighting.recalculation_required,
    )

    with pytest.raises(ValueError):
        _synthesize(
            candidate=candidate,
            validation=_validation(candidate),
            weighting=invalid,
            contradiction=_contradiction(candidate),
        )


def test_candidate_contradiction_id_mismatch_is_rejected():
    candidate = _candidate()
    contradiction = _contradiction(candidate)

    invalid = ContradictionAnalysisResult(
        candidate_id="different",
        contradiction_pairs=contradiction.contradiction_pairs,
        contradictory_evidence_ids=contradiction.contradictory_evidence_ids,
        contradictory_profiles=contradiction.contradictory_profiles,
        kind=contradiction.kind,
        outcome=contradiction.outcome,
        proposed_consolidation_outcome=contradiction.proposed_consolidation_outcome,
        temporal_resolution_explicit=contradiction.temporal_resolution_explicit,
        requires_review=contradiction.requires_review,
        preservation_required=contradiction.preservation_required,
        weighting_was_not_used_to_suppress_conflict=contradiction.weighting_was_not_used_to_suppress_conflict,
        reasons=contradiction.reasons,
    )

    with pytest.raises(ValueError):
        _synthesize(
            candidate=candidate,
            validation=_validation(candidate),
            weighting=_weighting(candidate),
            contradiction=invalid,
        )


def test_validation_evidence_set_must_match_candidate():
    candidate = _candidate()
    validation = _validation(candidate)

    invalid = EvidenceValidationResult(
        candidate_id=validation.candidate_id,
        evidence=validation.evidence[:1],
        valid_evidence_ids=("e-1",),
        invalid_evidence_ids=(),
        reasons=validation.reasons,
        contradictory_evidence_ids=(),
        temporal_incompatibility=False,
        provenance_complete=True,
        all_support_current=True,
        outcome=EvidenceValidationOutcome.ELIGIBLE,
        proposed_consolidation_outcome=ConsolidationOutcome.CANDIDATE,
    )

    with pytest.raises(ValueError):
        _synthesize(
            candidate=candidate,
            validation=invalid,
            weighting=_weighting(candidate),
            contradiction=_contradiction(candidate),
        )


def test_weighting_evidence_set_must_match_candidate():
    candidate = _candidate()
    weighting = _weighting(candidate)

    invalid = EvidenceWeightingResult(
        candidate_id=weighting.candidate_id,
        evidence=weighting.evidence[:1],
        ranked_evidence_ids=("e-1",),
        total_current_weight=0.7,
        current_support_count=1,
        independent_profile_count=1,
        contradiction_present=False,
        recalculation_required=False,
    )

    with pytest.raises(ValueError):
        _synthesize(
            candidate=candidate,
            validation=_validation(candidate),
            weighting=invalid,
            contradiction=_contradiction(candidate),
        )


def test_result_is_immutable():
    result = _synthesize()

    with pytest.raises(FrozenInstanceError):
        result.content = "changed"


def test_inputs_are_not_mutated():
    candidate = _candidate()
    validation = _validation(candidate)
    weighting = _weighting(candidate)
    contradiction = _contradiction(candidate)

    before = (
        candidate,
        validation,
        weighting,
        contradiction,
    )

    _synthesize(
        candidate=candidate,
        validation=validation,
        weighting=weighting,
        contradiction=contradiction,
    )

    after = (
        candidate,
        validation,
        weighting,
        contradiction,
    )

    assert before == after


def test_synthesis_id_is_deterministic():
    first = _synthesize()
    second = _synthesize()

    assert first.synthesis_id == second.synthesis_id


def test_content_is_trimmed():
    result = _synthesize(content="  Consolidated memory  ")

    assert result.content == "Consolidated memory"


def test_current_confidence_comes_from_weighting():
    result = _synthesize()

    assert result.confidence == 1.0


def test_confidence_is_zero_for_keep_separate():
    candidate = _candidate()
    contradiction = _contradiction(
        candidate,
        outcome=ContradictionOutcome.TEMPORALLY_SEPARATE,
        kind=ContradictionKind.TEMPORAL,
    )

    result = _synthesize(
        candidate=candidate,
        validation=_validation(candidate),
        weighting=_weighting(candidate),
        contradiction=contradiction,
    )

    assert result.confidence == 0.0


@pytest.mark.parametrize(
    "bad_argument",
    [
        "candidate",
        "validation",
        "weighting",
        "contradiction",
    ],
)
def test_input_types_are_validated(bad_argument):
    candidate = _candidate()
    validation = _validation(candidate)
    weighting = _weighting(candidate)
    contradiction = _contradiction(candidate)

    values = {
        "candidate": object(),
        "validation": object(),
        "weighting": object(),
        "contradiction": object(),
    }

    kwargs = {
        "candidate": candidate,
        "validation": validation,
        "weighting": weighting,
        "contradiction": contradiction,
        "content": "Consolidated memory",
    }
    kwargs[bad_argument] = values[bad_argument]

    with pytest.raises(TypeError):
        EvidencePreservingSynthesizer().synthesize(**kwargs)

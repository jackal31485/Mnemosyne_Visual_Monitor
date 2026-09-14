"""Tests for Phase 12E deterministic evidence weighting."""

from dataclasses import FrozenInstanceError

import pytest

from src.domain.consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)
from src.domain.evidence_validation import (
    EvidenceLifecycleState,
    EvidenceReference,
    EvidenceValidationResult,
    EvidenceValidationOutcome,
)
from src.domain.evidence_weighting import (
    EvidenceWeightReference,
    EvidenceWeightingPolicy,
    EvidenceWeightingStatus,
    EvidenceWeigher,
)
from src.domain.near_duplicate_detection import NearDuplicateDetector
from src.domain.observation_similarity import ObservationReference


def ref(observation_id: str, profile: str = "Horus") -> ObservationReference:
    return ObservationReference(
        observation_id=observation_id,
        source_profile=profile,
        evidence_id=f"evidence-{observation_id}",
    )


def make_validation(
    *,
    evidence: tuple[EvidenceReference, ...],
    invalid: tuple[str, ...] = (),
    contradictory: tuple[str, ...] = (),
) -> EvidenceValidationResult:
    return EvidenceValidationResult(
        candidate_id="candidate-1",
        evidence=evidence,
        valid_evidence_ids=tuple(
            item.evidence_id
            for item in evidence
            if item.evidence_id not in invalid
        ),
        invalid_evidence_ids=invalid,
        reasons=frozenset(),
        contradictory_evidence_ids=contradictory,
        temporal_incompatibility=False,
        provenance_complete=all(
            item.provenance_complete for item in evidence
        ),
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
            else (
                ConsolidationOutcome.REVIEW_REQUIRED
                if invalid
                else ConsolidationOutcome.CANDIDATE
            )
        ),
    )


def evidence(
    evidence_id: str,
    *,
    profile: str = "Horus",
    lifecycle: EvidenceLifecycleState = EvidenceLifecycleState.PROMOTED,
    provenance: bool = True,
) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_profile=profile,
        source_memory_id=f"memory-{evidence_id}",
        lifecycle_state=lifecycle,
        source_memory_exists=True,
        source_profile_authorized=True,
        provenance_complete=provenance,
        temporal_compatible=True,
        is_derived=False,
    )


def weight_reference(
    evidence_ref: EvidenceReference,
    *,
    confidence: float = 0.9,
    precision: float = 0.9,
    corroboration_count: int = 1,
    independent_source_count: int = 1,
    source_reliability: float | None = 0.9,
    temporal_recency: float | None = 0.9,
) -> EvidenceWeightReference:
    return EvidenceWeightReference(
        evidence=evidence_ref,
        confidence=confidence,
        precision=precision,
        corroboration_count=corroboration_count,
        independent_source_count=independent_source_count,
        source_reliability=source_reliability,
        temporal_recency=temporal_recency,
    )


def test_weighting_is_deterministic_and_explainable() -> None:
    item = evidence("evidence-1")
    validation = make_validation(evidence=(item,))
    reference = weight_reference(item)

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(reference,),
    )

    assert result.ranked_evidence_ids == ("evidence-1",)
    assert result.current_support_count == 1
    assert result.independent_profile_count == 1

    weighted = result.evidence[0]

    assert weighted.status is EvidenceWeightingStatus.CURRENT
    assert weighted.confidence == 0.9
    assert weighted.precision == 0.9
    assert weighted.reliability == 0.9
    assert weighted.recency == 0.9
    assert weighted.corroboration == pytest.approx(1 / 3)
    assert weighted.independence == pytest.approx(1 / 3)
    assert weighted.provenance == 1.0
    assert weighted.composite_weight == pytest.approx(
        0.9 * 0.20
        + 0.9 * 0.15
        + 0.9 * 0.15
        + 0.9 * 0.10
        + (1 / 3) * 0.15
        + (1 / 3) * 0.10
        + 1.0 * 0.15
    )


def test_custom_policy_changes_weight_only_by_declared_factors() -> None:
    item = evidence("evidence-1")
    validation = make_validation(evidence=(item,))

    policy = EvidenceWeightingPolicy(
        confidence_weight=1.0,
        precision_weight=0.0,
        reliability_weight=0.0,
        recency_weight=0.0,
        corroboration_weight=0.0,
        independence_weight=0.0,
        provenance_weight=0.0,
    )

    result = EvidenceWeigher(policy).weight(
        validation=validation,
        evidence=(weight_reference(item, confidence=0.73),),
    )

    assert result.evidence[0].composite_weight == 0.73


def test_weights_rank_stronger_evidence_first() -> None:
    strong = evidence("evidence-strong", profile="Horus")
    weak = evidence("evidence-weak", profile="Odin")

    validation = make_validation(
        evidence=(strong, weak),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(
                weak,
                confidence=0.4,
                precision=0.4,
                corroboration_count=0,
                independent_source_count=1,
                source_reliability=0.4,
                temporal_recency=0.4,
            ),
            weight_reference(
                strong,
                confidence=0.95,
                precision=0.95,
                corroboration_count=3,
                independent_source_count=3,
                source_reliability=0.95,
                temporal_recency=0.95,
            ),
        ),
    )

    assert result.ranked_evidence_ids == (
        "evidence-strong",
        "evidence-weak",
    )


def test_multiple_profiles_are_counted_as_independent_current_support() -> None:
    first = evidence("evidence-1", profile="Horus")
    second = evidence("evidence-2", profile="Odin")

    validation = make_validation(
        evidence=(first, second),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(first, independent_source_count=2),
            weight_reference(second, independent_source_count=2),
        ),
    )

    assert result.current_support_count == 2
    assert result.independent_profile_count == 2


def test_corroboration_is_bounded_and_deterministic() -> None:
    item = evidence("evidence-1")
    validation = make_validation(evidence=(item,))

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(
                item,
                corroboration_count=100,
                independent_source_count=100,
            ),
        ),
    )

    weighted = result.evidence[0]

    assert weighted.corroboration == 1.0
    assert weighted.independence == 1.0


def test_unavailable_optional_metadata_is_explicit() -> None:
    item = evidence("evidence-1")
    validation = make_validation(evidence=(item,))

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(
                item,
                source_reliability=None,
                temporal_recency=None,
            ),
        ),
    )

    weighted = result.evidence[0]

    assert weighted.reliability == 0.0
    assert weighted.recency == 0.0
    assert weighted.unavailable_signals == frozenset(
        {"source_reliability", "temporal_recency"}
    )
    assert "source_reliability_unavailable" in weighted.reasons
    assert "temporal_recency_unavailable" in weighted.reasons


def test_incomplete_provenance_reduces_weight_and_is_explained() -> None:
    item = evidence("evidence-1", provenance=False)

    validation = make_validation(
        evidence=(item,),
        invalid=("evidence-1",),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(weight_reference(item),),
    )

    weighted = result.evidence[0]

    assert weighted.status is EvidenceWeightingStatus.INELIGIBLE
    assert weighted.composite_weight == 0.0
    assert weighted.provenance == 0.0
    assert "incomplete_provenance" in weighted.reasons


def test_revoked_evidence_is_historical_not_current_support() -> None:
    item = evidence(
        "evidence-1",
        lifecycle=EvidenceLifecycleState.REVOKED,
    )

    validation = make_validation(
        evidence=(item,),
        invalid=("evidence-1",),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(weight_reference(item),),
    )

    weighted = result.evidence[0]

    assert weighted.status is EvidenceWeightingStatus.HISTORICAL
    assert weighted.composite_weight == 0.0
    assert result.current_support_count == 0
    assert result.recalculation_required is True
    assert "evidence_revoked" in weighted.reasons
    assert "revoked_historical_trace" in weighted.reasons


def test_unpromoted_evidence_cannot_receive_current_support_weight() -> None:
    item = evidence(
        "evidence-1",
        lifecycle=EvidenceLifecycleState.VALIDATED,
    )

    validation = make_validation(
        evidence=(item,),
        invalid=("evidence-1",),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(weight_reference(item),),
    )

    assert result.evidence[0].status is EvidenceWeightingStatus.INELIGIBLE
    assert result.evidence[0].composite_weight == 0.0
    assert result.current_support_count == 0


def test_contradiction_is_preserved_and_not_averaged_away() -> None:
    first = evidence("evidence-1", profile="Horus")
    second = evidence("evidence-2", profile="Odin")

    validation = make_validation(
        evidence=(first, second),
        contradictory=("evidence-2",),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(first, confidence=0.95),
            weight_reference(second, confidence=0.25),
        ),
    )

    assert result.contradiction_present is True
    assert result.current_support_count == 2
    assert result.ranked_evidence_ids[0] == "evidence-1"


def test_equal_weights_are_tie_broken_by_evidence_id() -> None:
    first = evidence("evidence-b")
    second = evidence("evidence-a")

    validation = make_validation(
        evidence=(first, second),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(first),
            weight_reference(second),
        ),
    )

    assert result.ranked_evidence_ids == (
        "evidence-a",
        "evidence-b",
    )


def test_total_current_weight_is_bounded() -> None:
    first = evidence("evidence-1")
    second = evidence("evidence-2")

    validation = make_validation(
        evidence=(first, second),
    )

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(
            weight_reference(first),
            weight_reference(second),
        ),
    )

    assert 0.0 <= result.total_current_weight <= 1.0


def test_weighting_result_is_immutable() -> None:
    item = evidence("evidence-1")
    validation = make_validation(evidence=(item,))

    result = EvidenceWeigher().weight(
        validation=validation,
        evidence=(weight_reference(item),),
    )

    with pytest.raises(FrozenInstanceError):
        result.current_support_count = 10  # type: ignore[misc]


def test_weight_reference_is_immutable() -> None:
    item = evidence("evidence-1")
    reference = weight_reference(item)

    with pytest.raises(FrozenInstanceError):
        reference.confidence = 0.1  # type: ignore[misc]


def test_invalid_policy_sum_is_rejected() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        EvidenceWeightingPolicy(
            confidence_weight=0.5,
            precision_weight=0.5,
            reliability_weight=0.5,
        )


def test_invalid_signal_bounds_are_rejected() -> None:
    item = evidence("evidence-1")

    with pytest.raises(ValueError):
        weight_reference(item, confidence=1.1)

    with pytest.raises(ValueError):
        weight_reference(item, precision=-0.1)


def test_weighting_requires_exact_validated_evidence_set() -> None:
    first = evidence("evidence-1")
    second = evidence("evidence-2")

    validation = make_validation(
        evidence=(first, second),
    )

    with pytest.raises(ValueError, match="exactly match"):
        EvidenceWeigher().weight(
            validation=validation,
            evidence=(weight_reference(first),),
        )


def test_weighting_requires_validation_result() -> None:
    item = evidence("evidence-1")

    with pytest.raises(TypeError):
        EvidenceWeigher().weight(
            validation=object(),  # type: ignore[arg-type]
            evidence=(weight_reference(item),),
        )


def test_weighting_requires_tuple_input() -> None:
    item = evidence("evidence-1")
    validation = make_validation(evidence=(item,))

    with pytest.raises(TypeError):
        EvidenceWeigher().weight(
            validation=validation,
            evidence=[weight_reference(item)],  # type: ignore[arg-type]
        )

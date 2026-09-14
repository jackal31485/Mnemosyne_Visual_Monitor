from dataclasses import FrozenInstanceError

import pytest

from src.domain.consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)
from src.domain.evidence_validation import (
    EvidenceLifecycleState,
    EvidenceReference,
    EvidenceValidationOutcome,
    EvidenceValidator,
)


def ref(
    observation_id: str,
    profile: str = "Horus",
    memory_id: str | None = None,
    evidence_id: str | None = None,
):
    from src.domain.observation_similarity import ObservationReference

    return ObservationReference(
        observation_id=observation_id,
        source_profile=profile,
        source_memory_id=memory_id or f"memory-{observation_id}",
        evidence_id=evidence_id or f"evidence-{observation_id}",
    )


def make_similarity():
    from src.domain.near_duplicate_detection import NearDuplicateDetector

    return NearDuplicateDetector().compare(
        left=ref("obs-1", evidence_id="evidence-1"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right=ref("obs-2", evidence_id="evidence-2"),
        right_text="SQLite is the authoritative Mnemosyne datastore layer.",
    ).similarity_result


def make_candidate(
    *,
    contradictory_evidence_ids=(),
    supporting_evidence_ids=("evidence-1", "evidence-2"),
):
    observations = (
        ref("obs-1", evidence_id="evidence-1"),
        ref("obs-2", evidence_id="evidence-2"),
    )
    return ConsolidationCandidate(
        candidate_id="candidate-1",
        observations=observations,
        similarity_result=make_similarity(),
        reasons=frozenset({"normalized_text_near_duplicate"}),
        entity_ids=(),
        relationship_ids=(),
        temporal_compatibility=1.0,
        supporting_evidence_ids=tuple(supporting_evidence_ids),
        contradictory_evidence_ids=tuple(contradictory_evidence_ids),
        source_profiles=("Horus",),
        confidence=0.90,
        proposed_outcome=ConsolidationOutcome.CANDIDATE,
        provenance_complete=True,
    )


def evidence(
    evidence_id: str,
    *,
    profile: str = "Horus",
    memory_id: str | None = None,
    lifecycle=EvidenceLifecycleState.PROMOTED,
    memory_exists=True,
    authorized=True,
    provenance=True,
    temporal=True,
    derived=False,
):
    return EvidenceReference(
        evidence_id=evidence_id,
        source_profile=profile,
        source_memory_id=memory_id or f"memory-{evidence_id}",
        lifecycle_state=lifecycle,
        source_memory_exists=memory_exists,
        source_profile_authorized=authorized,
        provenance_complete=provenance,
        temporal_compatible=temporal,
        is_derived=derived,
    )


def test_valid_promoted_evidence_is_eligible():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1"),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.ELIGIBLE
    assert result.is_eligible
    assert result.valid_evidence_ids == (
        "evidence-1",
        "evidence-2",
    )
    assert result.invalid_evidence_ids == ()
    assert result.all_support_current


def test_missing_source_memory_rejects_support():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1", memory_exists=False),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "source_memory_missing" in result.reasons
    assert "evidence-1" in result.invalid_evidence_ids


def test_unauthorized_profile_rejects_support():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1", authorized=False),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "source_profile_unauthorized" in result.reasons


def test_revoked_evidence_cannot_be_current_support():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence(
                "evidence-1",
                lifecycle=EvidenceLifecycleState.REVOKED,
            ),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "evidence_revoked" in result.reasons
    assert not result.all_support_current


def test_unpromoted_evidence_cannot_support_consolidation():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence(
                "evidence-1",
                lifecycle=EvidenceLifecycleState.VALIDATED,
            ),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "evidence_not_promoted" in result.reasons


def test_incomplete_provenance_rejects_support():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1", provenance=False),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "incomplete_provenance" in result.reasons
    assert not result.provenance_complete


def test_derived_statement_is_not_evidence():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1", derived=True),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "derived_statement_not_evidence" in result.reasons


def test_temporal_conflict_requires_review():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1", temporal=False),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REVIEW_REQUIRED
    assert result.requires_review
    assert "temporal_incompatibility" in result.reasons
    assert result.temporal_incompatibility
    assert (
        result.proposed_consolidation_outcome
        is ConsolidationOutcome.REVIEW_REQUIRED
    )


def test_unknown_temporal_compatibility_is_not_assumed_compatible():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1", temporal=None),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.REJECTED
    assert "temporal_compatibility_unknown" in result.reasons


def test_contradictory_evidence_requires_conflict_review():
    result = EvidenceValidator().validate(
        make_candidate(
            contradictory_evidence_ids=("evidence-3",),
            supporting_evidence_ids=("evidence-1", "evidence-2"),
        ),
        (
            evidence("evidence-1"),
            evidence("evidence-2"),
        ),
    )

    assert result.outcome is EvidenceValidationOutcome.CONFLICT
    assert result.requires_review
    assert result.contradictory_evidence_ids == ("evidence-3",)
    assert (
        result.proposed_consolidation_outcome
        is ConsolidationOutcome.CONFLICT
    )


def test_contradiction_is_preserved_not_hidden():
    result = EvidenceValidator().validate(
        make_candidate(contradictory_evidence_ids=("conflict-1",)),
        (
            evidence("evidence-1"),
            evidence("evidence-2"),
        ),
    )

    assert "contradictory_evidence_present" in result.reasons
    assert result.contradictory_evidence_ids == ("conflict-1",)


def test_missing_candidate_evidence_is_rejected_before_validation():
    with pytest.raises(ValueError, match="supporting evidence is missing"):
        EvidenceValidator().validate(
            make_candidate(
                supporting_evidence_ids=(
                    "evidence-1",
                    "evidence-2",
                    "evidence-3",
                )
            ),
            (
                evidence("evidence-1"),
                evidence("evidence-2"),
            ),
        )


def test_evidence_reference_is_immutable():
    item = evidence("evidence-1")

    with pytest.raises(FrozenInstanceError):
        item.evidence_id = "changed"


def test_validation_result_is_immutable():
    result = EvidenceValidator().validate(
        make_candidate(),
        (
            evidence("evidence-1"),
            evidence("evidence-2"),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        result.outcome = EvidenceValidationOutcome.REJECTED


def test_invalid_evidence_reference_state_is_rejected():
    with pytest.raises(ValueError, match="lifecycle_state"):
        EvidenceReference(
            evidence_id="evidence-1",
            source_profile="Horus",
            source_memory_id="memory-1",
            lifecycle_state="not-a-state",
            source_memory_exists=True,
            source_profile_authorized=True,
            provenance_complete=True,
            temporal_compatible=True,
        )


def test_non_tuple_evidence_input_is_rejected():
    with pytest.raises(TypeError, match="evidence must be a tuple"):
        EvidenceValidator().validate(
            make_candidate(),
            [evidence("evidence-1"), evidence("evidence-2")],
        )


def test_non_candidate_input_is_rejected():
    with pytest.raises(TypeError, match="candidate"):
        EvidenceValidator().validate(
            object(),
            (
                evidence("evidence-1"),
                evidence("evidence-2"),
            ),
        )

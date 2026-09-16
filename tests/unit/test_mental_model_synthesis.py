"""Phase 13F evidence-preserving mental-model synthesis tests."""

from datetime import datetime, timezone

import pytest

from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.mental_model_synthesis import (
    MentalModelSynthesisError,
    MentalModelSynthesizer,
)


def _validated_model() -> MentalModel:
    provenance = MentalModelProvenance(
        derivation_method="phase-13c-validation",
        observation_ids=("obs-1", "obs-2"),
        evidence_ids=("ev-1", "ev-2"),
        memory_ids=("mem-1", "mem-2"),
        source_profiles=("profile-a",),
        entity_ids=("entity-1",),
        relationship_ids=("rel-1",),
    )

    return MentalModel(
        model_id="model-1",
        model_type=MentalModelType.PATTERN,
        title="Recurring workflow pattern",
        description="Validated pattern.",
        entity_ids=("entity-1",),
        relationship_ids=("rel-1",),
        supporting_observation_ids=("obs-1", "obs-2"),
        supporting_evidence_ids=("ev-1", "ev-2"),
        supporting_memory_ids=("mem-1", "mem-2"),
        source_profiles=("profile-a",),
        temporal_scope=("2026",),
        confidence=0.86,
        status=MentalModelStatus.VALIDATED,
        version=1,
        created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        provenance=provenance,
        derivation_method="phase-13c-validation",
        contradictory_evidence_ids=(),
    )


def test_synthesis_activates_validated_model():
    model = _validated_model()

    result = MentalModelSynthesizer.synthesize(
        model,
        title="Recurring workflow pattern",
        description="The governed evidence indicates a recurring workflow.",
        synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
    )

    assert result.is_valid
    assert result.synthesized_model.status is MentalModelStatus.ACTIVE
    assert result.synthesized_model.is_derived
    assert result.synthesized_model.is_currently_retrievable


def test_synthesis_preserves_complete_evidence_chain():
    model = _validated_model()

    result = MentalModelSynthesizer.synthesize(
        model,
        title="Pattern",
        description="Derived pattern description.",
        synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
    )

    synthesized = result.synthesized_model

    assert synthesized.supporting_observation_ids == model.supporting_observation_ids
    assert synthesized.supporting_evidence_ids == model.supporting_evidence_ids
    assert synthesized.supporting_memory_ids == model.supporting_memory_ids
    assert synthesized.source_profiles == model.source_profiles
    assert synthesized.entity_ids == model.entity_ids
    assert synthesized.relationship_ids == model.relationship_ids
    assert synthesized.temporal_scope == model.temporal_scope
    assert synthesized.contradictory_evidence_ids == model.contradictory_evidence_ids


def test_synthesis_rebuilds_provenance_without_losing_lineage():
    model = _validated_model()

    result = MentalModelSynthesizer.synthesize(
        model,
        title="Pattern",
        description="Derived pattern description.",
        synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
    )

    provenance = result.synthesized_model.provenance

    assert provenance.derivation_method == (
        "phase-13f-evidence-preserving-synthesis"
    )
    assert provenance.observation_ids == model.supporting_observation_ids
    assert provenance.evidence_ids == model.supporting_evidence_ids
    assert provenance.memory_ids == model.supporting_memory_ids
    assert provenance.source_profiles == model.source_profiles
    assert provenance.entity_ids == model.entity_ids
    assert provenance.relationship_ids == model.relationship_ids


def test_synthesis_does_not_mutate_source_model():
    model = _validated_model()

    result = MentalModelSynthesizer.synthesize(
        model,
        title="New derived title",
        description="New derived description.",
        synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
    )

    assert result.source_model is model
    assert model.status is MentalModelStatus.VALIDATED
    assert model.title == "Recurring workflow pattern"
    assert model.description == "Validated pattern."
    assert model.provenance.derivation_method == "phase-13c-validation"


def test_synthesis_rejects_candidate_model():
    model = _validated_model().transition_to(MentalModelStatus.REVOKED)

    with pytest.raises(MentalModelSynthesisError):
        MentalModelSynthesizer.synthesize(
            model,
            title="Pattern",
            description="Derived pattern.",
            synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        )


def test_synthesis_rejects_empty_description():
    with pytest.raises(ValueError):
        MentalModelSynthesizer.synthesize(
            _validated_model(),
            title="Pattern",
            description="   ",
            synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        )


def test_synthesis_can_explicitly_preserve_or_update_confidence():
    model = _validated_model()

    result = MentalModelSynthesizer.synthesize(
        model,
        title="Pattern",
        description="Derived pattern.",
        synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        confidence=0.91,
    )

    assert result.synthesized_model.confidence == 0.91


def test_synthesis_rejects_missing_supporting_evidence():
    model = _validated_model()

    broken = MentalModel(
        model_id=model.model_id,
        model_type=model.model_type,
        title=model.title,
        description=model.description,
        entity_ids=model.entity_ids,
        relationship_ids=model.relationship_ids,
        supporting_observation_ids=model.supporting_observation_ids,
        supporting_evidence_ids=model.supporting_evidence_ids,
        supporting_memory_ids=model.supporting_memory_ids,
        source_profiles=model.source_profiles,
        temporal_scope=model.temporal_scope,
        confidence=model.confidence,
        status=model.status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        provenance=model.provenance,
        derivation_method=model.derivation_method,
        contradictory_evidence_ids=model.contradictory_evidence_ids,
    )

    # The contract permits VALIDATED models without active-support invariants;
    # synthesis must still require evidence explicitly.
    object.__setattr__(broken, "supporting_evidence_ids", ())

    with pytest.raises(MentalModelSynthesisError):
        MentalModelSynthesizer.synthesize(
            broken,
            title="Pattern",
            description="Derived pattern.",
            synthesized_at=datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc),
        )

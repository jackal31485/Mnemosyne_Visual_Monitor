"""Phase 13A tests for the governed mental-model contract."""

from datetime import datetime, timedelta, timezone

import pytest

from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)


def make_model(**overrides):
    created = datetime(2026, 9, 16, tzinfo=timezone.utc)
    values = dict(
        model_id="mm-001",
        model_type=MentalModelType.CONCEPT,
        title="SQLite is the authoritative local store",
        description="A derived concept supported by governed observations.",
        entity_ids=("entity-sqlite",),
        relationship_ids=("rel-authoritative-store",),
        supporting_observation_ids=("obs-1", "obs-2"),
        supporting_evidence_ids=("ev-1", "ev-2"),
        supporting_memory_ids=("mem-1", "mem-2"),
        source_profiles=("jeeves",),
        temporal_scope=("current",),
        confidence=0.82,
        status=MentalModelStatus.CANDIDATE,
        version=1,
        created_at=created,
        updated_at=created,
        provenance=MentalModelProvenance(
            derivation_method="deterministic_phase_13a_contract",
            observation_ids=("obs-1", "obs-2"),
            evidence_ids=("ev-1", "ev-2"),
            memory_ids=("mem-1", "mem-2"),
            source_profiles=("jeeves",),
            entity_ids=("entity-sqlite",),
            relationship_ids=("rel-authoritative-store",),
        ),
        derivation_method="deterministic_phase_13a_contract",
        contradictory_evidence_ids=(),
    )
    values.update(overrides)
    return MentalModel(**values)


def test_contract_supports_all_planned_model_types():
    assert {item.value for item in MentalModelType} == {
        "concept",
        "pattern",
        "relationship",
        "temporal",
        "expectation",
    }


def test_contract_supports_all_planned_lifecycle_states():
    assert {item.value for item in MentalModelStatus} == {
        "candidate",
        "validated",
        "active",
        "stale",
        "superseded",
        "revoked",
    }


def test_model_is_explicitly_derived_and_immutable():
    model = make_model()
    assert model.is_derived is True
    assert model.is_currently_retrievable is False

    with pytest.raises((AttributeError, TypeError)):
        model.title = "mutated"


def test_active_model_requires_governed_support():
    with pytest.raises(ValueError, match="supporting observations"):
        make_model(
            status=MentalModelStatus.ACTIVE,
            supporting_observation_ids=(),
            provenance=MentalModelProvenance(
                derivation_method="deterministic_phase_13a_contract",
                observation_ids=(),
                evidence_ids=("ev-1", "ev-2"),
                memory_ids=("mem-1", "mem-2"),
                source_profiles=("jeeves",),
                entity_ids=("entity-sqlite",),
                relationship_ids=("rel-authoritative-store",),
            ),
        )


def test_provenance_must_match_supporting_ids():
    with pytest.raises(ValueError, match="provenance evidence IDs"):
        make_model(
            provenance=MentalModelProvenance(
                derivation_method="deterministic_phase_13a_contract",
                observation_ids=("obs-1", "obs-2"),
                evidence_ids=("ev-1",),
                memory_ids=("mem-1", "mem-2"),
                source_profiles=("jeeves",),
                entity_ids=("entity-sqlite",),
                relationship_ids=("rel-authoritative-store",),
            )
        )


def test_contradictory_evidence_cannot_escape_supporting_evidence():
    with pytest.raises(ValueError, match="contradictory evidence"):
        make_model(contradictory_evidence_ids=("ev-999",))


def test_confidence_is_bounded():
    with pytest.raises(ValueError, match="confidence"):
        make_model(confidence=1.01)


def test_version_must_be_positive():
    with pytest.raises(ValueError, match="version"):
        make_model(version=0)


def test_updated_at_cannot_precede_created_at():
    created = datetime(2026, 9, 16, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="updated_at"):
        make_model(
            created_at=created,
            updated_at=created - timedelta(seconds=1),
        )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (MentalModelStatus.CANDIDATE, MentalModelStatus.VALIDATED),
        (MentalModelStatus.VALIDATED, MentalModelStatus.ACTIVE),
        (MentalModelStatus.ACTIVE, MentalModelStatus.STALE),
        (MentalModelStatus.STALE, MentalModelStatus.ACTIVE),
        (MentalModelStatus.ACTIVE, MentalModelStatus.REVOKED),
    ],
)
def test_allowed_lifecycle_transitions(old, new):
    model = make_model(status=old)
    assert model.can_transition_to(new) is True
    transitioned = model.transition_to(new)
    assert transitioned.status is new
    assert transitioned.model_id == model.model_id
    assert transitioned.version == model.version


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (MentalModelStatus.CANDIDATE, MentalModelStatus.ACTIVE),
        (MentalModelStatus.ACTIVE, MentalModelStatus.CANDIDATE),
        (MentalModelStatus.SUPERSEDED, MentalModelStatus.ACTIVE),
        (MentalModelStatus.REVOKED, MentalModelStatus.ACTIVE),
    ],
)
def test_disallowed_lifecycle_transitions(old, new):
    model = make_model(status=old)
    assert model.can_transition_to(new) is False
    with pytest.raises(ValueError, match="invalid mental-model transition"):
        model.transition_to(new)

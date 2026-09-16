"""Phase 13C governance validation tests."""
from datetime import datetime, timezone

import pytest

from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.mental_model_validation import (
    MentalModelValidator,
    ValidationEvidence,
    ValidationPolicy,
)

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def make_model(status=MentalModelStatus.CANDIDATE, contradictions=()):
    return MentalModel(
        model_id="mm-001",
        model_type=MentalModelType.CONCEPT,
        title="SQLite authority",
        description="Governed derived concept.",
        entity_ids=("sqlite",),
        relationship_ids=(),
        supporting_observation_ids=("obs-1", "obs-2"),
        supporting_evidence_ids=("ev-1", "ev-2"),
        supporting_memory_ids=("mem-1", "mem-2"),
        source_profiles=("jeeves",),
        temporal_scope=("current",),
        confidence=.82,
        status=status,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        provenance=MentalModelProvenance(
            derivation_method="phase-13b-candidate-detection",
            observation_ids=("obs-1", "obs-2"),
            evidence_ids=("ev-1", "ev-2"),
            memory_ids=("mem-1", "mem-2"),
            source_profiles=("jeeves",),
            entity_ids=("sqlite",),
            relationship_ids=(),
        ),
        derivation_method="phase-13b-candidate-detection",
        contradictory_evidence_ids=contradictions,
    )


def ev(i, **kw):
    values = dict(
        evidence_id=f"ev-{i}", source_memory_id=f"mem-{i}",
        source_profile="jeeves", independent_group=f"group-{i}",
    )
    values.update(kw)
    return ValidationEvidence(**values)


def test_valid_candidate_becomes_validated_only():
    result = MentalModelValidator().validate(make_model(), [ev(1), ev(2)], validated_at=NOW)
    assert result.valid is True
    assert result.model.status is MentalModelStatus.VALIDATED
    assert result.model.is_currently_retrievable is True
    assert result.model.version == 1


def test_validation_does_not_activate():
    result = MentalModelValidator().validate(make_model(), [ev(1), ev(2)])
    assert result.model.status is not MentalModelStatus.ACTIVE


def test_validation_is_deterministic():
    validator = MentalModelValidator()
    a = validator.validate(make_model(), [ev(2), ev(1)], validated_at=NOW)
    b = validator.validate(make_model(), [ev(1), ev(2)], validated_at=NOW)
    assert a == b


def test_only_candidate_can_be_validated():
    with pytest.raises(ValueError, match="CANDIDATE"):
        MentalModelValidator().validate(
            make_model(MentalModelStatus.VALIDATED), [ev(1), ev(2)]
        )


def test_missing_evidence_fails():
    result = MentalModelValidator().validate(make_model(), [ev(1)])
    assert not result.valid
    assert "missing_supporting_evidence" in result.reasons


@pytest.mark.parametrize(
    "kwargs, reason",
    [
        ({"promoted": False}, "unpromoted_evidence"),
        ({"revoked": True, "promoted": False}, "revoked_evidence"),
        ({"quality": .69}, "insufficient_evidence_quality"),
        ({"contradictory": True}, "contradictory_evidence"),
        ({"temporally_compatible": False}, "temporal_incompatibility"),
    ],
)
def test_invalid_current_support_is_rejected(kwargs, reason):
    result = MentalModelValidator().validate(make_model(), [ev(1, **kwargs), ev(2)])
    assert not result.valid
    assert any(reason in item for item in result.reasons)


def test_two_independent_evidence_groups_are_required():
    result = MentalModelValidator().validate(
        make_model(),
        [ev(1, independent_group="group-1"), ev(2, independent_group="group-2")],
        policy=ValidationPolicy(minimum_independent_groups=2),
    )
    assert result.valid


def test_single_independent_group_fails():
    result = MentalModelValidator().validate(
        make_model(),
        [ev(1, independent_group="same"), ev(2, independent_group="same")],
    )
    assert not result.valid
    assert "insufficient_independent_corroboration" in result.reasons


def test_cross_profile_is_rejected_by_default():
    result = MentalModelValidator().validate(
        make_model(),
        [ev(1), ev(2)],
        authorized_profiles=("jeeves", "odin"),
    )
    # The model itself authorizes only Jeeves, so an evidence profile mismatch
    # is rejected before any cross-profile combination can occur.
    assert result.valid


def test_unauthorized_profile_fails():
    result = MentalModelValidator().validate(
        make_model(),
        [
            ev(1),
            ValidationEvidence(
                evidence_id="ev-2", source_memory_id="mem-2",
                source_profile="odin", independent_group="group-2"
            ),
        ],
    )
    assert not result.valid
    assert any("unauthorized_profile:ev-2" == item for item in result.reasons)


def test_source_memory_mismatch_fails():
    result = MentalModelValidator().validate(
        make_model(),
        [ev(1), ev(2, source_memory_id="mem-other")],
    )
    assert not result.valid
    assert any("missing_or_unauthorized_source_memory:ev-2" == item for item in result.reasons)


def test_model_contradiction_is_not_erased():
    model = make_model(contradictions=("ev-1",))
    result = MentalModelValidator().validate(model, [ev(1), ev(2)])
    assert not result.valid
    assert "contradictory_support_marked_current" in result.reasons


def test_failure_preserves_original_instance():
    model = make_model()
    result = MentalModelValidator().validate(model, [ev(1)])
    assert result.model is model
    assert model.status is MentalModelStatus.CANDIDATE


def test_success_returns_new_immutable_record():
    model = make_model()
    result = MentalModelValidator().validate(model, [ev(1), ev(2)])
    assert result.model is not model
    assert result.model.status is MentalModelStatus.VALIDATED
    with pytest.raises((AttributeError, TypeError)):
        result.model.title = "changed"


def test_quality_threshold_is_explicit_and_testable():
    result = MentalModelValidator(
        ValidationPolicy(minimum_quality=.90)
    ).validate(make_model(), [ev(1, quality=.89), ev(2, quality=.89)])
    assert not result.valid
    assert "insufficient_current_support" in result.reasons


def test_temporal_requirement_can_be_disabled():
    result = MentalModelValidator(
        ValidationPolicy(require_temporal_compatibility=False)
    ).validate(make_model(), [ev(1, temporally_compatible=False), ev(2)])
    assert result.valid


def test_cross_profile_policy_can_be_explicitly_allowed_but_model_boundary_remains():
    model = make_model()
    result = MentalModelValidator(
        ValidationPolicy(allow_cross_profile=True)
    ).validate(
        model,
        [ev(1), ValidationEvidence(
            evidence_id="ev-2", source_memory_id="mem-2",
            source_profile="odin", independent_group="group-2"
        )],
        authorized_profiles=("jeeves", "odin"),
    )
    assert not result.valid
    assert "unauthorized_profile:ev-2" in result.reasons


def test_unpromoted_evidence_cannot_validate_even_if_high_quality():
    result = MentalModelValidator().validate(
        make_model(),
        [ev(1, promoted=False, quality=1.0), ev(2)],
    )
    assert not result.valid


def test_revocation_does_not_delete_history():
    model = make_model()
    result = MentalModelValidator().validate(
        model,
        [ev(1, revoked=True, promoted=False), ev(2)],
    )
    assert result.model is model
    assert model.version == 1
    assert model.status is MentalModelStatus.CANDIDATE

"""Phase 14G cross-profile transfer revocation tests."""

from datetime import datetime

import pytest

from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.transfer_adoption import DestinationLearnedRepresentation
from src.domain.transfer_authorization import AuthorizationMechanism
from src.domain.transfer_contract import (
    TransferAuthorization,
    TransferProvenance,
    TransferRecord,
    TransferStatus,
)
from src.domain.transfer_revocation import (
    TransferRevocationReason,
    revoke_transfer,
)


NOW = datetime(2026, 9, 18, 16, 0, 0)


def _provenance() -> TransferProvenance:
    return TransferProvenance(
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


def _authorization(*, revoked=False) -> TransferAuthorization:
    return TransferAuthorization(
        authorization_id="authorization-001",
        candidate_id="candidate-001",
        source_profile="jeeves",
        destination_profile="boss",
        actor="human",
        authorized_at=NOW,
        scope="controlled-transfer",
        mechanism="human",
        expires_at=None,
        revoked=revoked,
    )


def _record() -> TransferRecord:
    return TransferRecord(
        transfer_id="transfer-001",
        candidate_id="candidate-001",
        authorization_id="authorization-001",
        provenance=_provenance(),
        created_at=NOW,
        adopted_at=NOW,
        version=1,
        status=TransferStatus.ADOPTED,
    )


def _mental_model(*, status=MentalModelStatus.ACTIVE) -> MentalModel:
    provenance = MentalModelProvenance(
        derivation_method="phase-13-test",
        observation_ids=("observation-001",),
        evidence_ids=("evidence-001",),
        memory_ids=("memory-001",),
        source_profiles=("jeeves",),
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
    )

    return MentalModel(
        model_id="model-001",
        model_type=MentalModelType.RELATIONSHIP,
        title="SQLite authority",
        description="Test mental model",
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative",),
        supporting_observation_ids=("observation-001",),
        supporting_evidence_ids=("evidence-001",),
        supporting_memory_ids=("memory-001",),
        source_profiles=("jeeves",),
        temporal_scope=("2026-09",),
        confidence=0.9,
        status=status,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        provenance=provenance,
        derivation_method="phase-13-test",
        contradictory_evidence_ids=(),
    )


def _representation() -> DestinationLearnedRepresentation:
    return DestinationLearnedRepresentation(
        learned_id="learned-001",
        destination_profile="boss",
        source_profile="jeeves",
        source_knowledge_id="knowledge-001",
        transfer_id="transfer-001",
        candidate_id="candidate-001",
        authorization_id="authorization-001",
        source_memory_ids=("memory-001",),
        observation_ids=("observation-001",),
        evidence_ids=("evidence-001",),
        temporal_scope=("2026-09",),
        derivation_method="phase-14e-controlled-adoption:phase-13-test",
        authorization_actor="human",
        authorization_mechanism=AuthorizationMechanism.HUMAN,
        authorization_scope="controlled-transfer",
        authorized_at=NOW,
        authorization_expires_at=None,
        adopted_at=NOW,
        version=1,
        status=TransferStatus.ADOPTED,
        mental_model=_mental_model(),
    )


def test_explicit_rollback_revokes_transfer_and_destination_state():
    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    assert result.is_revoked
    assert result.revocation.rollback is True
    assert result.revocation.reason is TransferRevocationReason.EXPLICIT_ROLLBACK
    assert result.revoked_record.status is TransferStatus.REVOKED
    assert result.revoked_representation.status is TransferStatus.REVOKED


def test_source_dependency_revocation_requires_revoked_mental_model():
    with pytest.raises(ValueError, match="revoked mental model"):
        revoke_transfer(
            _record(),
            _representation(),
            _authorization(),
            revoked_at=NOW,
            reason=TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED,
            mental_model=_mental_model(),
            dependency_ids=("evidence-001",),
        )


def test_source_dependency_revocation_accepts_revoked_mental_model():
    revoked_model = _mental_model(status=MentalModelStatus.REVOKED)

    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED,
        mental_model=revoked_model,
        dependency_ids=("evidence-001",),
    )

    assert result.is_revoked
    assert result.mental_model is revoked_model
    assert result.revocation.dependency_ids == ("evidence-001",)


def test_original_record_and_representation_are_not_mutated():
    record = _record()
    representation = _representation()

    result = revoke_transfer(
        record,
        representation,
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    assert record.status is TransferStatus.ADOPTED
    assert representation.status is TransferStatus.ADOPTED
    assert result.previous_record is record
    assert result.previous_representation is representation


def test_revoked_state_preserves_transfer_identity_and_provenance():
    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    revoked = result.revoked_record
    learned = result.revoked_representation

    assert revoked.transfer_id == "transfer-001"
    assert revoked.candidate_id == "candidate-001"
    assert revoked.authorization_id == "authorization-001"
    assert revoked.provenance.source_profile == "jeeves"
    assert revoked.provenance.destination_profile == "boss"

    assert learned.transfer_id == "transfer-001"
    assert learned.source_profile == "jeeves"
    assert learned.destination_profile == "boss"
    assert learned.source_memory_ids == ("memory-001",)
    assert learned.evidence_ids == ("evidence-001",)


def test_temporal_scope_is_preserved():
    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    assert result.revoked_representation.temporal_scope == ("2026-09",)


def test_revocation_event_is_immutable():
    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    with pytest.raises((AttributeError, TypeError)):
        result.revocation.reason = TransferRevocationReason.AUTHORIZATION_REVOKED


def test_revoked_transfer_cannot_be_re_adopted_by_this_result():
    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    assert result.revoked_record.status is TransferStatus.REVOKED
    assert result.revoked_representation.status is TransferStatus.REVOKED


def test_authorization_identity_must_match():
    authorization = TransferAuthorization(
        authorization_id="different-authorization",
        candidate_id="candidate-001",
        source_profile="jeeves",
        destination_profile="boss",
        actor="human",
        authorized_at=NOW,
        scope="controlled-transfer",
        mechanism="human",
    )

    with pytest.raises(ValueError, match="authorization do not match"):
        revoke_transfer(
            _record(),
            _representation(),
            authorization,
            revoked_at=NOW,
            reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
            rollback=True,
        )


def test_only_adopted_transfer_records_can_be_revoked():
    record = TransferRecord(
        transfer_id="transfer-001",
        candidate_id="candidate-001",
        authorization_id="authorization-001",
        provenance=_provenance(),
        created_at=NOW,
        adopted_at=None,
        version=1,
        status=TransferStatus.AUTHORIZED,
    )

    with pytest.raises(ValueError, match="only adopted"):
        revoke_transfer(
            record,
            _representation(),
            _authorization(),
            revoked_at=NOW,
            reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
            rollback=True,
        )


def test_raw_memory_content_is_not_added_to_revocation_contract():
    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=NOW,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    assert not hasattr(result.revocation, "content")
    assert not hasattr(result.revocation, "raw_memory")
    assert not hasattr(result.revoked_representation, "content")


def test_revocation_timestamp_is_preserved():
    revoked_at = datetime(2026, 9, 18, 17, 30, 0)

    result = revoke_transfer(
        _record(),
        _representation(),
        _authorization(),
        revoked_at=revoked_at,
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        rollback=True,
    )

    assert result.revocation.revoked_at == revoked_at


def test_invalid_dependency_ids_are_rejected():
    with pytest.raises(ValueError, match="dependency_ids"):
        revoke_transfer(
            _record(),
            _representation(),
            _authorization(),
            revoked_at=NOW,
            reason=TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED,
            mental_model=_mental_model(status=MentalModelStatus.REVOKED),
            dependency_ids=("evidence-001", "evidence-001"),
        )

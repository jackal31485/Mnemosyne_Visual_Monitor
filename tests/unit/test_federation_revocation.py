from datetime import datetime, timezone

import pytest

from src.domain.federation_exchange import (
    FederationExchangeEnvelope,
    FederationExchangeKind,
    FederationExchangeState,
    FederationKnowledgeReceipt,
    FederationProvenance,
)
from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)
from src.domain.federation_revocation import (
    FederationRevocationError,
    FederationRevocationSignal,
    propagate_federation_revocation,
)
from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)
from src.domain.transfer_adoption import DestinationLearnedRepresentation
from src.domain.transfer_authorization import (
    AuthorizationMechanism,
    TransferAuthorization,
)
from src.domain.transfer_contract import TransferRecord, TransferStatus
from src.domain.transfer_revocation import TransferRevocationReason


def _participants():
    sender = FederationParticipant(
        participant_id="remote-node",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )
    recipient = FederationParticipant(
        participant_id="local-node",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )
    return sender, recipient


def _fixtures():
    sender, recipient = _participants()
    provenance = FederationProvenance(
        source_participant_id="remote-node",
        source_memory_id="memory-1",
        source_profile_id="remote-profile",
        originating_exchange_id="exchange-revocation-1",
    )
    envelope = FederationExchangeEnvelope(
        exchange_id="exchange-revocation-1",
        sender=sender,
        recipient=recipient,
        kind=FederationExchangeKind.OBSERVATION,
        provenance=provenance,
        payload={"revocation": True},
    )
    receipt = FederationKnowledgeReceipt(
        exchange_id=envelope.exchange_id,
        recipient=recipient,
        state=FederationExchangeState.VALIDATED,
        provenance=provenance,
    )

    adopted_at = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    revoked_at = datetime(2026, 9, 20, 13, tzinfo=timezone.utc)

    authorization = TransferAuthorization(
        authorization_id="auth-1",
        candidate_id="candidate-1",
        source_profile="remote-profile",
        destination_profile="local-profile",
        actor="reviewer",
        authorized_at=adopted_at,
        scope="knowledge",
    )

    record = TransferRecord(
        transfer_id="transfer-1",
        candidate_id="candidate-1",
        authorization_id="auth-1",
        provenance=_transfer_provenance(),
        created_at=adopted_at,
        adopted_at=adopted_at,
        status=TransferStatus.ADOPTED,
    )

    mental_model = MentalModel(
        model_id="model-1",
        model_type=MentalModelType.CONCEPT,
        title="Test model",
        description="Test federation revocation model",
        entity_ids=(),
        relationship_ids=(),
        supporting_observation_ids=("observation-1",),
        supporting_evidence_ids=("evidence-1",),
        supporting_memory_ids=("memory-1",),
        source_profiles=("remote-profile",),
        temporal_scope=(),
        confidence=0.9,
        status=MentalModelStatus.VALIDATED,
        version=1,
        created_at=adopted_at,
        updated_at=adopted_at,
        provenance=MentalModelProvenance(
            derivation_method="test",
            observation_ids=("observation-1",),
            evidence_ids=("evidence-1",),
            memory_ids=("memory-1",),
            source_profiles=("remote-profile",),
        ),
        derivation_method="test",
        contradictory_evidence_ids=(),
    )

    representation = DestinationLearnedRepresentation(
        learned_id="learned-1",
        destination_profile="local-profile",
        source_profile="remote-profile",
        source_knowledge_id="knowledge-1",
        transfer_id="transfer-1",
        candidate_id="candidate-1",
        authorization_id="auth-1",
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
        evidence_ids=("evidence-1",),
        temporal_scope=(),
        derivation_method="test",
        authorization_actor="reviewer",
        authorization_mechanism=AuthorizationMechanism.HUMAN,
        authorization_scope="knowledge",
        authorized_at=adopted_at,
        authorization_expires_at=None,
        adopted_at=adopted_at,
        version=1,
        status=TransferStatus.ADOPTED,
        mental_model=mental_model,
    )

    signal = FederationRevocationSignal(
        revocation_id="federation-revocation-1",
        source_participant_id="remote-node",
        source_profile="remote-profile",
        destination_profile="local-profile",
        transfer_id="transfer-1",
        candidate_id="candidate-1",
        authorization_id="auth-1",
        learned_id="learned-1",
        source_knowledge_id="knowledge-1",
        source_memory_ids=("memory-1",),
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        revoked_at=revoked_at,
        originating_exchange_id="exchange-revocation-1",
    )

    return (
        envelope,
        receipt,
        recipient,
        record,
        representation,
        authorization,
        signal,
    )


def _transfer_provenance():
    from src.domain.transfer_contract import TransferProvenance

    return TransferProvenance(
        source_profile="remote-profile",
        destination_profile="local-profile",
        source_knowledge_id="knowledge-1",
        transfer_candidate_id="candidate-1",
        transfer_record_id="transfer-1",
        evidence_ids=("evidence-1",),
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
    )


def test_validated_federation_revocation_delegates_to_phase_14():
    (
        _,
        receipt,
        recipient,
        record,
        representation,
        authorization,
        signal,
    ) = _fixtures()

    propagation = propagate_federation_revocation(
        signal,
        receipt=receipt,
        recipient=recipient,
        record=record,
        representation=representation,
        authorization=authorization,
    )

    assert propagation.is_revoked
    assert propagation.result.revoked_record.status is TransferStatus.REVOKED
    assert propagation.result.revoked_representation.is_currently_retrievable is False
    assert propagation.result.revocation.reason is (
        TransferRevocationReason.EXPLICIT_ROLLBACK
    )


def test_original_history_is_not_mutated():
    (
        _,
        receipt,
        recipient,
        record,
        representation,
        authorization,
        signal,
    ) = _fixtures()

    propagate_federation_revocation(
        signal,
        receipt=receipt,
        recipient=recipient,
        record=record,
        representation=representation,
        authorization=authorization,
    )

    assert record.status is TransferStatus.ADOPTED
    assert representation.status is TransferStatus.ADOPTED


def test_unvalidated_receipt_cannot_propagate():
    (
        _,
        receipt,
        recipient,
        record,
        representation,
        authorization,
        signal,
    ) = _fixtures()

    rejected = FederationKnowledgeReceipt(
        exchange_id=receipt.exchange_id,
        recipient=recipient,
        state=FederationExchangeState.REJECTED,
        provenance=receipt.provenance,
        rejection_reason="invalid",
    )

    with pytest.raises(FederationRevocationError):
        propagate_federation_revocation(
            signal,
            receipt=rejected,
            recipient=recipient,
            record=record,
            representation=representation,
            authorization=authorization,
        )


def test_lineage_mismatch_is_rejected():
    (
        _,
        receipt,
        recipient,
        record,
        representation,
        authorization,
        signal,
    ) = _fixtures()

    mismatched = FederationRevocationSignal(
        revocation_id=signal.revocation_id,
        source_participant_id=signal.source_participant_id,
        source_profile=signal.source_profile,
        destination_profile=signal.destination_profile,
        transfer_id=signal.transfer_id,
        candidate_id=signal.candidate_id,
        authorization_id=signal.authorization_id,
        learned_id=signal.learned_id,
        source_knowledge_id="different-knowledge",
        source_memory_ids=signal.source_memory_ids,
        reason=signal.reason,
        revoked_at=signal.revoked_at,
        originating_exchange_id=signal.originating_exchange_id,
    )

    with pytest.raises(FederationRevocationError):
        propagate_federation_revocation(
            mismatched,
            receipt=receipt,
            recipient=recipient,
            record=record,
            representation=representation,
            authorization=authorization,
        )


def test_source_dependency_revocation_requires_dependency_ids():
    with pytest.raises(ValueError):
        FederationRevocationSignal(
            revocation_id="revocation-1",
            source_participant_id="remote-node",
            source_profile="remote-profile",
            destination_profile="local-profile",
            transfer_id="transfer-1",
            candidate_id="candidate-1",
            authorization_id="auth-1",
            learned_id="learned-1",
            source_knowledge_id="knowledge-1",
            source_memory_ids=("memory-1",),
            reason=TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED,
            revoked_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
            originating_exchange_id="exchange-1",
        )


def test_signal_is_immutable():
    *_, signal = _fixtures()

    with pytest.raises(AttributeError):
        signal.learned_id = "different"


def test_signal_preserves_source_attribution():
    *_, signal = _fixtures()

    assert signal.source_participant_id == "remote-node"
    assert signal.source_profile == "remote-profile"
    assert signal.source_memory_ids == ("memory-1",)


def test_revocation_result_preserves_federation_lineage():
    (
        _,
        receipt,
        recipient,
        record,
        representation,
        authorization,
        signal,
    ) = _fixtures()

    propagation = propagate_federation_revocation(
        signal,
        receipt=receipt,
        recipient=recipient,
        record=record,
        representation=representation,
        authorization=authorization,
    )

    assert propagation.signal.revocation_id == "federation-revocation-1"
    assert propagation.result.revocation.transfer_id == signal.transfer_id
    assert propagation.result.revocation.learned_id == signal.learned_id

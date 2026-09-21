from datetime import datetime, timezone

import pytest

from src.domain.federation_adoption import (
    FederationAdoptionError,
    FederationKnowledgeProjection,
    propose_federation_adoption,
)
from src.domain.federation_exchange import (
    FederationExchangeEnvelope,
    FederationExchangeKind,
    FederationKnowledgeReceipt,
    validate_exchange_envelope,
    FederationProvenance,
    FederationExchangeState,
)
from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)


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


def _exchange():
    sender, recipient = _participants()

    provenance = FederationProvenance(
        source_participant_id=sender.participant_id,
        source_memory_id="memory-1",
        source_profile_id="remote-profile",
        originating_exchange_id="exchange-1",
    )

    envelope = FederationExchangeEnvelope(
        exchange_id="exchange-1",
        sender=sender,
        recipient=recipient,
        kind=FederationExchangeKind.OBSERVATION,
        provenance=provenance,
        payload={"observation_id": "obs-1"},
    )

    receipt = FederationKnowledgeReceipt(
        exchange_id="exchange-1",
        recipient=recipient,
        state=FederationExchangeState.VALIDATED,
        provenance=provenance,
    )

    return envelope, receipt


def _proposal():
    envelope, receipt = _exchange()

    return propose_federation_adoption(
        envelope,
        receipt,
        destination_profile="local-profile",
        source_profile="remote-profile",
        source_knowledge_id="knowledge-1",
        source_memory_ids=("memory-1",),
        observation_ids=("obs-1",),
        evidence_ids=("evidence-1",),
        applicability="candidate",
    )


def test_validated_receipt_creates_candidate_and_proposed_projection():
    proposal = _proposal()

    assert proposal.candidate.status.value == "candidate"
    assert proposal.projection.status == "PROPOSED"
    assert proposal.projection.transfer_candidate_id == proposal.candidate.candidate_id
    assert proposal.projection.transfer_record_id == (
        proposal.candidate.provenance.transfer_record_id
    )


def test_receipt_does_not_imply_adoption():
    proposal = _proposal()

    assert proposal.is_adopted is False
    assert proposal.projection.is_proposed is True
    assert proposal.projection.is_adopted is False


def test_invalid_receipt_state_is_rejected():
    envelope, receipt = _exchange()

    rejected = FederationKnowledgeReceipt(
        exchange_id=receipt.exchange_id,
        recipient=receipt.recipient,
        state=FederationExchangeState.REJECTED,
        provenance=receipt.provenance,
        rejection_reason="test",
    )

    with pytest.raises(FederationAdoptionError):
        propose_federation_adoption(
            envelope,
            rejected,
            destination_profile="local-profile",
            source_profile="remote-profile",
            source_knowledge_id="knowledge-1",
            source_memory_ids=("memory-1",),
            observation_ids=("obs-1",),
            evidence_ids=("evidence-1",),
            applicability="candidate",
        )


def test_exchange_identity_must_match_receipt():
    envelope, receipt = _exchange()

    mismatched_envelope = FederationExchangeEnvelope(
        exchange_id="other-exchange",
        sender=envelope.sender,
        recipient=envelope.recipient,
        kind=envelope.kind,
        provenance=FederationProvenance(
            source_participant_id=envelope.sender.participant_id,
            source_memory_id=envelope.provenance.source_memory_id,
            source_profile_id=envelope.provenance.source_profile_id,
            originating_exchange_id="other-exchange",
        ),
        payload=envelope.payload,
    )

    mismatched_receipt = validate_exchange_envelope(
        mismatched_envelope,
        recipient=envelope.recipient,
    )

    with pytest.raises(ValueError, match="exchange"):
        propose_federation_adoption(
            envelope,
            mismatched_receipt,
            destination_profile="local-profile",
            source_profile="remote-profile",
            source_knowledge_id="knowledge-1",
            source_memory_ids=("memory-1",),
            observation_ids=("obs-1",),
            evidence_ids=("evidence-1",),
            applicability="candidate",
        )


def test_source_memory_from_federation_provenance_is_required():
    envelope, receipt = _exchange()

    with pytest.raises(FederationAdoptionError):
        propose_federation_adoption(
            envelope,
            receipt,
            destination_profile="local-profile",
            source_profile="remote-profile",
            source_knowledge_id="knowledge-1",
            source_memory_ids=("different-memory",),
            observation_ids=("obs-1",),
            evidence_ids=("evidence-1",),
            applicability="candidate",
        )


def test_projection_preserves_attribution():
    proposal = _proposal()

    assert proposal.projection.source_participant_id == "remote-node"
    assert proposal.projection.source_profile == "remote-profile"
    assert proposal.projection.source_memory_ids == ("memory-1",)
    assert proposal.projection.observation_ids == ("obs-1",)
    assert proposal.projection.evidence_ids == ("evidence-1",)


def test_projection_contains_no_raw_payload():
    proposal = _proposal()

    assert not hasattr(proposal.projection, "payload")
    assert not hasattr(proposal.projection, "content")


def test_projection_is_immutable():
    projection = _proposal().projection

    with pytest.raises(AttributeError):
        projection.status = "ADOPTED"


def test_source_and_destination_profiles_must_differ():
    envelope, receipt = _exchange()

    with pytest.raises(ValueError):
        propose_federation_adoption(
            envelope,
            receipt,
            destination_profile="remote-profile",
            source_profile="remote-profile",
            source_knowledge_id="knowledge-1",
            source_memory_ids=("memory-1",),
            observation_ids=("obs-1",),
            evidence_ids=("evidence-1",),
            applicability="candidate",
        )


def test_empty_projection_evidence_is_rejected():
    with pytest.raises(ValueError):
        FederationKnowledgeProjection(
            projection_id="projection-1",
            destination_profile="local-profile",
            source_participant_id="remote-node",
            source_profile="remote-profile",
            source_knowledge_id="knowledge-1",
            source_memory_ids=("memory-1",),
            observation_ids=("obs-1",),
            evidence_ids=(),
            transfer_candidate_id="candidate-1",
            transfer_record_id="record-1",
        )

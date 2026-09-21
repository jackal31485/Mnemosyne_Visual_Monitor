import pytest

from src.domain.federation_exchange import (
    FederationExchangeEnvelope,
    FederationExchangeKind,
    FederationExchangeState,
    FederationKnowledgeReceipt,
    FederationProvenance,
    receive_remote_knowledge,
    validate_exchange_envelope,
)
from src.domain.federation_authorization import (
    FederationCapability,
    authorize_participant,
)
from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)
from src.domain.federation_session import (
    authenticate_federation_session,
    unauthenticated_federation_session,
)


@pytest.fixture
def sender():
    return FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )


@pytest.fixture
def recipient():
    return FederationParticipant(
        participant_id="local-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )


@pytest.fixture
def provenance():
    return FederationProvenance(
        source_participant_id="remote-001",
        source_memory_id="memory-001",
        source_profile_id="profile-001",
        originating_exchange_id="exchange-001",
    )


@pytest.fixture
def envelope(sender, recipient, provenance):
    return FederationExchangeEnvelope(
        exchange_id="exchange-001",
        sender=sender,
        recipient=recipient,
        kind=FederationExchangeKind.OBSERVATION,
        provenance=provenance,
        payload={"observation_id": "observation-001"},
    )


def test_envelope_carries_explicit_provenance(envelope, provenance):
    assert envelope.provenance == provenance
    assert envelope.kind is FederationExchangeKind.OBSERVATION


def test_provenance_source_matches_sender(envelope, sender):
    assert (
        envelope.provenance.source_participant_id
        == sender.participant_id
    )


def test_exchange_id_must_match_provenance(provenance, sender, recipient):
    bad_provenance = FederationProvenance(
        source_participant_id="remote-001",
        source_memory_id="memory-001",
        source_profile_id="profile-001",
        originating_exchange_id="different-exchange",
    )

    with pytest.raises(ValueError):
        FederationExchangeEnvelope(
            exchange_id="exchange-001",
            sender=sender,
            recipient=recipient,
            kind=FederationExchangeKind.OBSERVATION,
            provenance=bad_provenance,
            payload={},
        )


def test_recipient_mismatch_is_rejected(
    envelope,
    sender,
):
    other_recipient = FederationParticipant(
        participant_id="other-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )

    receipt = validate_exchange_envelope(
        envelope,
        recipient=other_recipient,
    )

    assert receipt.state is FederationExchangeState.REJECTED
    assert receipt.rejection_reason == "recipient mismatch"


def test_matching_recipient_is_validated(
    envelope,
    recipient,
):
    receipt = validate_exchange_envelope(
        envelope,
        recipient=recipient,
    )

    assert receipt.state is FederationExchangeState.VALIDATED
    assert receipt.is_validated is True
    assert receipt.rejection_reason is None


def test_receive_remote_knowledge_rejects_unauthenticated_session(
    sender,
    recipient,
):
    envelope = FederationExchangeEnvelope(
        exchange_id="exchange-001",
        sender=sender,
        recipient=recipient,
        kind=FederationExchangeKind.OBSERVATION,
        provenance=FederationProvenance(
            source_participant_id=sender.participant_id,
            source_memory_id="memory-001",
            source_profile_id="profile-001",
            originating_exchange_id="exchange-001",
        ),
        payload={"fact": "test"},
    )
    session = unauthenticated_federation_session(
        participant=recipient,
        session_id="session-001",
    )
    authorization = authorize_participant(
        participant=recipient,
        capabilities=frozenset({FederationCapability.RECEIVE_KNOWLEDGE}),
    )

    with pytest.raises(PermissionError):
        receive_remote_knowledge(
            envelope,
            recipient=recipient,
            session=session,
            authorization=authorization,
        )


def test_receive_remote_knowledge_rejects_authenticated_session_without_capability(
    envelope,
    recipient,
):
    session = authenticate_federation_session(
        participant=recipient,
        session_id="session-001",
        authenticated_at=100,
        expires_at=200,
    )
    authorization = authorize_participant(
        participant=recipient,
        capabilities=frozenset(),
    )

    with pytest.raises(PermissionError, match="missing federation capability"):
        receive_remote_knowledge(
            envelope,
            recipient=recipient,
            session=session,
            authorization=authorization,
        )


def test_receive_remote_knowledge_uses_validation_boundary(
    envelope,
    recipient,
):
    session = authenticate_federation_session(
        participant=recipient,
        session_id="session-001",
        authenticated_at=100,
        expires_at=200,
    )
    authorization = authorize_participant(
        participant=recipient,
        capabilities=frozenset({FederationCapability.RECEIVE_KNOWLEDGE}),
    )

    receipt = receive_remote_knowledge(
        envelope,
        recipient=recipient,
        session=session,
        authorization=authorization,
    )

    assert isinstance(receipt, FederationKnowledgeReceipt)
    assert receipt.state is FederationExchangeState.VALIDATED


def test_receipt_does_not_imply_adoption(
    envelope,
    recipient,
):
    session = authenticate_federation_session(
        participant=recipient,
        session_id="session-001",
        authenticated_at=100,
        expires_at=200,
    )
    authorization = authorize_participant(
        participant=recipient,
        capabilities=frozenset({FederationCapability.RECEIVE_KNOWLEDGE}),
    )

    receipt = receive_remote_knowledge(
        envelope,
        recipient=recipient,
        session=session,
        authorization=authorization,
    )

    assert receipt.is_adoptable is False


def test_rejected_receipt_requires_reason(
    envelope,
    recipient,
):
    with pytest.raises(ValueError):
        FederationKnowledgeReceipt(
            exchange_id=envelope.exchange_id,
            recipient=recipient,
            state=FederationExchangeState.REJECTED,
            provenance=envelope.provenance,
        )


def test_invalid_provenance_is_rejected():
    with pytest.raises(ValueError):
        FederationProvenance(
            source_participant_id="",
            source_memory_id="memory-001",
            source_profile_id="profile-001",
            originating_exchange_id="exchange-001",
        )


def test_invalid_payload_type_is_rejected(
    sender,
    recipient,
    provenance,
):
    with pytest.raises(TypeError):
        FederationExchangeEnvelope(
            exchange_id="exchange-001",
            sender=sender,
            recipient=recipient,
            kind=FederationExchangeKind.OBSERVATION,
            provenance=provenance,
            payload=None,  # type: ignore[arg-type]
        )


def test_envelope_is_immutable(envelope):
    with pytest.raises(AttributeError):
        envelope.exchange_id = "changed"  # type: ignore[misc]


def test_receipt_is_immutable(envelope, recipient):
    session = authenticate_federation_session(
        participant=recipient,
        session_id="session-001",
        authenticated_at=100,
        expires_at=200,
    )
    authorization = authorize_participant(
        participant=recipient,
        capabilities=frozenset({FederationCapability.RECEIVE_KNOWLEDGE}),
    )

    receipt = receive_remote_knowledge(
        envelope,
        recipient=recipient,
        session=session,
        authorization=authorization,
    )

    with pytest.raises(AttributeError):
        receipt.state = FederationExchangeState.REJECTED  # type: ignore[misc]

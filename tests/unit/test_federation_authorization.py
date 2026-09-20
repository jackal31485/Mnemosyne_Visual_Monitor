import pytest

from src.domain.federation_authorization import (
    FederationAuthorization,
    FederationCapability,
    authorize_participant,
)
from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)


@pytest.fixture
def participant():
    return FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )


def test_participant_can_receive_explicit_capabilities(participant):
    authorization = authorize_participant(
        participant=participant,
        capabilities=frozenset(
            {
                FederationCapability.READ_COLLECTIVE,
                FederationCapability.REQUEST_KNOWLEDGE,
            }
        ),
    )

    assert authorization.has_capability(
        FederationCapability.READ_COLLECTIVE
    )
    assert authorization.has_capability(
        FederationCapability.REQUEST_KNOWLEDGE
    )


def test_capability_is_not_granted_by_default(participant):
    authorization = authorize_participant(participant=participant)

    assert not authorization.has_capability(
        FederationCapability.READ_COLLECTIVE
    )


def test_capabilities_are_participant_specific(participant):
    other = FederationParticipant(
        participant_id="remote-002",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )

    first = authorize_participant(
        participant=participant,
        capabilities=frozenset(
            {FederationCapability.READ_COLLECTIVE}
        ),
    )
    second = authorize_participant(participant=other)

    assert first.has_capability(FederationCapability.READ_COLLECTIVE)
    assert not second.has_capability(FederationCapability.READ_COLLECTIVE)


def test_with_capability_returns_new_authorization(participant):
    original = authorize_participant(participant=participant)

    updated = original.with_capability(
        FederationCapability.READ_COLLECTIVE
    )

    assert not original.has_capability(
        FederationCapability.READ_COLLECTIVE
    )
    assert updated.has_capability(
        FederationCapability.READ_COLLECTIVE
    )


def test_without_capability_returns_new_authorization(participant):
    original = authorize_participant(
        participant=participant,
        capabilities=frozenset(
            {FederationCapability.READ_COLLECTIVE}
        ),
    )

    updated = original.without_capability(
        FederationCapability.READ_COLLECTIVE
    )

    assert original.has_capability(
        FederationCapability.READ_COLLECTIVE
    )
    assert not updated.has_capability(
        FederationCapability.READ_COLLECTIVE
    )


def test_invalid_capability_type_is_rejected(participant):
    authorization = authorize_participant(participant=participant)

    with pytest.raises(TypeError):
        authorization.has_capability("READ_COLLECTIVE")  # type: ignore[arg-type]


def test_invalid_participant_is_rejected():
    with pytest.raises(TypeError):
        authorize_participant(participant="remote-001")  # type: ignore[arg-type]


def test_invalid_capability_collection_is_rejected(participant):
    with pytest.raises(TypeError):
        authorize_participant(
            participant=participant,
            capabilities={FederationCapability.READ_COLLECTIVE},  # type: ignore[arg-type]
        )


def test_invalid_capability_member_is_rejected(participant):
    with pytest.raises(TypeError):
        authorize_participant(
            participant=participant,
            capabilities=frozenset({"READ_COLLECTIVE"}),  # type: ignore[arg-type]
        )


def test_authorization_is_immutable(participant):
    authorization = authorize_participant(
        participant=participant,
        capabilities=frozenset(
            {FederationCapability.READ_COLLECTIVE}
        ),
    )

    with pytest.raises(AttributeError):
        authorization.capabilities = frozenset()  # type: ignore[misc]


def test_authorization_is_not_authentication(participant):
    authorization = authorize_participant(
        participant=participant,
        capabilities=frozenset(
            {FederationCapability.READ_COLLECTIVE}
        ),
    )

    assert isinstance(authorization, FederationAuthorization)
    assert authorization.has_capability(
        FederationCapability.READ_COLLECTIVE
    )

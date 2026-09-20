import pytest

from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
    FederationPeerState,
)
from src.domain.federation_trust import (
    FederationTrustRecord,
    FederationTrustState,
    establish_federation_trust,
    trust_state_for_peer,
)


@pytest.fixture
def participant():
    return FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )


def test_trust_can_be_explicitly_established(participant):
    trust = establish_federation_trust(
        participant=participant,
        established_at=100,
        expires_at=200,
        reason="manually verified",
    )

    assert trust.state is FederationTrustState.TRUSTED
    assert trust.is_trusted is True
    assert trust.established_at == 100
    assert trust.expires_at == 200


def test_trust_does_not_grant_exchange_eligibility(participant):
    trust = establish_federation_trust(
        participant=participant,
        established_at=100,
    )

    assert trust.is_exchange_eligible is False
    assert trust_state_for_peer(trust) is FederationPeerState.TRUST_ESTABLISHED


def test_trust_can_expire(participant):
    trust = establish_federation_trust(
        participant=participant,
        established_at=100,
        expires_at=200,
    )

    expired = trust.expire()

    assert expired.state is FederationTrustState.EXPIRED
    assert expired.is_expired is True
    assert expired.is_trusted is False


def test_trust_can_be_blocked(participant):
    trust = establish_federation_trust(
        participant=participant,
        established_at=100,
    )

    blocked = trust.block("operator blocked peer")

    assert blocked.state is FederationTrustState.BLOCKED
    assert blocked.is_blocked is True
    assert trust_state_for_peer(blocked) is FederationPeerState.BLOCKED


def test_trust_can_be_revoked(participant):
    trust = establish_federation_trust(
        participant=participant,
        established_at=100,
    )

    revoked = trust.revoke("trust withdrawn")

    assert revoked.state is FederationTrustState.REVOKED
    assert revoked.is_revoked is True
    assert trust_state_for_peer(revoked) is FederationPeerState.REVOKED


def test_untrusted_maps_to_identified(participant):
    trust = FederationTrustRecord(
        participant=participant,
        state=FederationTrustState.UNTRUSTED,
    )

    assert trust_state_for_peer(trust) is FederationPeerState.IDENTIFIED


def test_expiration_must_follow_establishment(participant):
    with pytest.raises(ValueError):
        establish_federation_trust(
            participant=participant,
            established_at=200,
            expires_at=100,
        )


def test_invalid_timestamp_type_is_rejected(participant):
    with pytest.raises(TypeError):
        establish_federation_trust(
            participant=participant,
            established_at="100",  # type: ignore[arg-type]
        )


def test_trust_record_is_immutable(participant):
    trust = establish_federation_trust(
        participant=participant,
        established_at=100,
    )

    with pytest.raises(AttributeError):
        trust.state = FederationTrustState.REVOKED  # type: ignore[misc]

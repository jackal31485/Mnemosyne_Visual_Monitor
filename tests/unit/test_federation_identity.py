import pytest

from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
    FederationPeer,
    FederationPeerState,
)


def test_participant_requires_explicit_identity_and_type():
    participant = FederationParticipant(
        participant_id="mnemosyne:loki",
        participant_type=(
            FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE
        ),
    )

    assert participant.participant_id == "mnemosyne:loki"
    assert (
        participant.participant_type
        is FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE
    )


def test_all_participant_types_are_explicit():
    assert {
        member.value
        for member in FederationParticipantType
    } == {
        "LOCAL_MODEL",
        "LOCAL_PROFILE",
        "REMOTE_MNEMOSYNE_INSTANCE",
        "REMOTE_AGENT_SERVICE",
    }


def test_discovery_is_distinct_from_trust_authentication_and_authorization():
    assert FederationPeerState.DISCOVERED is not FederationPeerState.TRUST_ESTABLISHED
    assert FederationPeerState.TRUST_ESTABLISHED is not FederationPeerState.AUTHENTICATED
    assert FederationPeerState.AUTHENTICATED is not FederationPeerState.AUTHORIZED
    assert FederationPeerState.AUTHORIZED is not FederationPeerState.EXCHANGE_ELIGIBLE


def test_peer_exposes_participant_identity_without_endpoint_data():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.DISCOVERED,
    )

    assert peer.participant_id == "remote-001"
    assert (
        peer.participant_type
        is FederationParticipantType.REMOTE_AGENT_SERVICE
    )
    assert peer.state is FederationPeerState.DISCOVERED
    assert peer.is_exchange_eligible is False


def test_exchange_eligibility_requires_explicit_final_state():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.EXCHANGE_ELIGIBLE,
    )

    assert peer.is_exchange_eligible is True


@pytest.mark.parametrize(
    "state",
    [
        FederationPeerState.BLOCKED,
        FederationPeerState.REVOKED,
        FederationPeerState.EXPIRED,
    ],
)
def test_terminal_negative_states_are_never_exchange_eligible(state):
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    peer = FederationPeer(
        participant=participant,
        state=state,
    )

    assert peer.is_exchange_eligible is False


def test_empty_participant_id_is_rejected():
    with pytest.raises(ValueError):
        FederationParticipant(
            participant_id="",
            participant_type=FederationParticipantType.LOCAL_MODEL,
        )


def test_non_string_participant_id_is_rejected():
    with pytest.raises(TypeError):
        FederationParticipant(
            participant_id=123,  # type: ignore[arg-type]
            participant_type=FederationParticipantType.LOCAL_MODEL,
        )


def test_invalid_participant_type_is_rejected():
    with pytest.raises(TypeError):
        FederationParticipant(
            participant_id="local-model",
            participant_type="LOCAL_MODEL",  # type: ignore[arg-type]
        )


def test_invalid_peer_state_is_rejected():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    with pytest.raises(TypeError):
        FederationPeer(
            participant=participant,
            state="DISCOVERED",  # type: ignore[arg-type]
        )


def test_discovered_peer_must_be_identified_before_trust():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.DISCOVERED,
    )

    from src.domain.federation_identity import transition_peer_state

    peer = transition_peer_state(
        peer,
        FederationPeerState.IDENTIFIED,
    )

    assert peer.state is FederationPeerState.IDENTIFIED


def test_full_federation_lifecycle_requires_each_stage():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.DISCOVERED,
    )

    from src.domain.federation_identity import transition_peer_state

    expected = [
        FederationPeerState.IDENTIFIED,
        FederationPeerState.TRUST_ESTABLISHED,
        FederationPeerState.AUTHENTICATED,
        FederationPeerState.AUTHORIZED,
        FederationPeerState.EXCHANGE_ELIGIBLE,
    ]

    for state in expected:
        peer = transition_peer_state(peer, state)

    assert peer.state is FederationPeerState.EXCHANGE_ELIGIBLE
    assert peer.is_exchange_eligible is True


def test_discovery_cannot_skip_directly_to_exchange_eligibility():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.DISCOVERED,
    )

    from src.domain.federation_identity import transition_peer_state

    with pytest.raises(ValueError):
        transition_peer_state(
            peer,
            FederationPeerState.EXCHANGE_ELIGIBLE,
        )


def test_identified_cannot_skip_trust_and_authentication():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.IDENTIFIED,
    )

    from src.domain.federation_identity import transition_peer_state

    with pytest.raises(ValueError):
        transition_peer_state(
            peer,
            FederationPeerState.AUTHORIZED,
        )


def test_terminal_negative_states_cannot_become_exchange_eligible():
    participant = FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    from src.domain.federation_identity import transition_peer_state

    for state in (
        FederationPeerState.BLOCKED,
        FederationPeerState.REVOKED,
        FederationPeerState.EXPIRED,
    ):
        peer = FederationPeer(
            participant=participant,
            state=state,
        )

        with pytest.raises(ValueError):
            transition_peer_state(
                peer,
                FederationPeerState.EXCHANGE_ELIGIBLE,
            )

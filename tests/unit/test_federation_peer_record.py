import pytest

from src.domain.federation_identity import (
    FederationParticipantType,
    FederationPeerState,
)
from src.domain.federation_peer_record import (
    FederationPeerRecord,
    federation_peer_from_discovery,
)


def test_discovery_record_creates_distinct_federation_peer():
    record = federation_peer_from_discovery(
        client_id="remote-001",
        hostname="remote-host",
        address="192.168.2.200",
        api_port=8000,
        first_seen=100,
        last_seen=200,
        discovery_state="DISCOVERED",
    )

    assert record.participant_id == "remote-001"
    assert (
        record.participant_type
        is FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE
    )
    assert record.federation_state is FederationPeerState.DISCOVERED


def test_legacy_adopted_state_does_not_grant_exchange_eligibility():
    record = federation_peer_from_discovery(
        client_id="remote-001",
        hostname="remote-host",
        address="192.168.2.200",
        api_port=8000,
        first_seen=100,
        last_seen=200,
        discovery_state="ADOPTED",
    )

    assert record.federation_state is FederationPeerState.DISCOVERED
    assert record.is_exchange_eligible is False


def test_discovery_metadata_is_kept_separate_from_identity():
    record = federation_peer_from_discovery(
        client_id="remote-001",
        hostname="remote-host",
        address="192.168.2.200",
        api_port=8000,
        first_seen=100,
        last_seen=200,
        discovery_state="ADOPTED",
    )

    assert record.discovery_client_id == "remote-001"
    assert record.hostname == "remote-host"
    assert record.address == "192.168.2.200"
    assert record.api_port == 8000

    assert not hasattr(record.peer, "hostname")
    assert not hasattr(record.peer, "address")
    assert not hasattr(record.peer, "api_port")


def test_remote_agent_service_can_be_represented_without_special_transport_logic():
    record = federation_peer_from_discovery(
        client_id="friday-001",
        hostname="friday",
        address="192.168.2.210",
        api_port=9000,
        first_seen=100,
        last_seen=200,
        discovery_state="DISCOVERED",
        participant_type=FederationParticipantType.REMOTE_AGENT_SERVICE,
    )

    assert (
        record.participant_type
        is FederationParticipantType.REMOTE_AGENT_SERVICE
    )
    assert record.federation_state is FederationPeerState.DISCOVERED


@pytest.mark.parametrize("state", ["DISCOVERED", "ADOPTED"])
def test_legacy_discovery_states_never_directly_create_exchange_eligible_peer(
    state,
):
    record = federation_peer_from_discovery(
        client_id="remote-001",
        hostname=None,
        address=None,
        api_port=None,
        first_seen=None,
        last_seen=None,
        discovery_state=state,
    )

    assert record.is_exchange_eligible is False


def test_invalid_discovery_state_type_is_rejected():
    with pytest.raises(TypeError):
        federation_peer_from_discovery(
            client_id="remote-001",
            hostname=None,
            address=None,
            api_port=None,
            first_seen=None,
            last_seen=None,
            discovery_state=None,  # type: ignore[arg-type]
        )


def test_empty_discovery_client_id_is_rejected():
    with pytest.raises(ValueError):
        federation_peer_from_discovery(
            client_id="",
            hostname=None,
            address=None,
            api_port=None,
            first_seen=None,
            last_seen=None,
            discovery_state="DISCOVERED",
        )


def test_invalid_api_port_is_rejected():
    with pytest.raises(ValueError):
        federation_peer_from_discovery(
            client_id="remote-001",
            hostname=None,
            address=None,
            api_port=70000,
            first_seen=None,
            last_seen=None,
            discovery_state="DISCOVERED",
        )


def test_record_is_immutable():
    record = federation_peer_from_discovery(
        client_id="remote-001",
        hostname="remote-host",
        address="192.168.2.200",
        api_port=8000,
        first_seen=100,
        last_seen=200,
        discovery_state="DISCOVERED",
    )

    with pytest.raises(AttributeError):
        record.hostname = "changed"  # type: ignore[misc]

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
    FederationPeer,
    FederationPeerState,
)


@dataclass(frozen=True)
class FederationPeerRecord:
    """
    Federation view of a discovered peer.

    Discovery metadata is retained as transport/linkage information.
    It does not establish federation trust, authentication,
    authorization, or exchange eligibility.
    """

    peer: FederationPeer
    discovery_client_id: str
    hostname: Optional[str]
    address: Optional[str]
    api_port: Optional[int]
    first_seen: Optional[int]
    last_seen: Optional[int]

    def __post_init__(self) -> None:
        if not isinstance(self.discovery_client_id, str):
            raise TypeError("discovery_client_id must be a string")

        if not self.discovery_client_id.strip():
            raise ValueError(
                "discovery_client_id must not be empty"
            )

        if self.hostname is not None and not isinstance(
            self.hostname,
            str,
        ):
            raise TypeError("hostname must be a string or None")

        if self.address is not None and not isinstance(
            self.address,
            str,
        ):
            raise TypeError("address must be a string or None")

        if self.api_port is not None and (
            not isinstance(self.api_port, int)
            or not 1 <= self.api_port <= 65535
        ):
            raise ValueError(
                "api_port must be an integer between 1 and 65535"
            )

        for field_name, value in (
            ("first_seen", self.first_seen),
            ("last_seen", self.last_seen),
        ):
            if value is not None and not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer or None"
                )

    @property
    def participant(self) -> FederationParticipant:
        return self.peer.participant

    @property
    def participant_id(self) -> str:
        return self.peer.participant_id

    @property
    def participant_type(self) -> FederationParticipantType:
        return self.peer.participant_type

    @property
    def federation_state(self) -> FederationPeerState:
        return self.peer.state

    @property
    def is_exchange_eligible(self) -> bool:
        return self.peer.is_exchange_eligible


def federation_peer_from_discovery(
    *,
    client_id: str,
    hostname: Optional[str],
    address: Optional[str],
    api_port: Optional[int],
    first_seen: Optional[int],
    last_seen: Optional[int],
    discovery_state: str,
    participant_type: FederationParticipantType = (
        FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE
    ),
) -> FederationPeerRecord:
    """
    Create a federation peer from existing discovery metadata.

    Legacy discovery adoption is deliberately NOT mapped to federation
    exchange eligibility. Every discovered peer begins the federation
    lifecycle in DISCOVERED state.
    """

    if not isinstance(discovery_state, str):
        raise TypeError("discovery_state must be a string")

    participant = FederationParticipant(
        participant_id=client_id,
        participant_type=participant_type,
    )

    peer = FederationPeer(
        participant=participant,
        state=FederationPeerState.DISCOVERED,
    )

    return FederationPeerRecord(
        peer=peer,
        discovery_client_id=client_id,
        hostname=hostname,
        address=address,
        api_port=api_port,
        first_seen=first_seen,
        last_seen=last_seen,
    )

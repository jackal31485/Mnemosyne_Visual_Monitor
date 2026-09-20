from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FederationParticipantType(str, Enum):
    """Type of participant visible to the federation layer."""

    LOCAL_MODEL = "LOCAL_MODEL"
    LOCAL_PROFILE = "LOCAL_PROFILE"
    REMOTE_MNEMOSYNE_INSTANCE = "REMOTE_MNEMOSYNE_INSTANCE"
    REMOTE_AGENT_SERVICE = "REMOTE_AGENT_SERVICE"


class FederationPeerState(str, Enum):
    """
    Federation lifecycle state.

    Discovery is intentionally not equivalent to trust, authentication,
    authorization, or exchange eligibility.
    """

    DISCOVERED = "DISCOVERED"
    IDENTIFIED = "IDENTIFIED"
    TRUST_ESTABLISHED = "TRUST_ESTABLISHED"
    AUTHENTICATED = "AUTHENTICATED"
    AUTHORIZED = "AUTHORIZED"
    EXCHANGE_ELIGIBLE = "EXCHANGE_ELIGIBLE"

    BLOCKED = "BLOCKED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


# Valid forward federation lifecycle transitions.
#
# Discovery, identity, trust, authentication, authorization, and exchange
# eligibility remain distinct. There is deliberately no direct transition
# from discovery to exchange eligibility.
FEDERATION_PEER_TRANSITIONS: dict[
    FederationPeerState,
    frozenset[FederationPeerState],
] = {
    FederationPeerState.DISCOVERED: frozenset(
        {FederationPeerState.IDENTIFIED}
    ),
    FederationPeerState.IDENTIFIED: frozenset(
        {FederationPeerState.TRUST_ESTABLISHED}
    ),
    FederationPeerState.TRUST_ESTABLISHED: frozenset(
        {FederationPeerState.AUTHENTICATED}
    ),
    FederationPeerState.AUTHENTICATED: frozenset(
        {FederationPeerState.AUTHORIZED}
    ),
    FederationPeerState.AUTHORIZED: frozenset(
        {FederationPeerState.EXCHANGE_ELIGIBLE}
    ),
    FederationPeerState.EXCHANGE_ELIGIBLE: frozenset(),
    FederationPeerState.BLOCKED: frozenset(),
    FederationPeerState.REVOKED: frozenset(),
    FederationPeerState.EXPIRED: frozenset(),
}


def can_transition_peer_state(
    current: FederationPeerState,
    target: FederationPeerState,
) -> bool:
    """Return whether a federation peer may advance to *target*."""

    if not isinstance(current, FederationPeerState):
        raise TypeError("current must be a FederationPeerState")

    if not isinstance(target, FederationPeerState):
        raise TypeError("target must be a FederationPeerState")

    return target in FEDERATION_PEER_TRANSITIONS[current]


def transition_peer_state(
    peer: "FederationPeer",
    target: FederationPeerState,
) -> "FederationPeer":
    """Return a new peer in an explicitly permitted lifecycle state."""

    if not can_transition_peer_state(peer.state, target):
        raise ValueError(
            f"Invalid federation peer transition: "
            f"{peer.state.value} -> {target.value}"
        )

    return FederationPeer(
        participant=peer.participant,
        state=target,
    )


@dataclass(frozen=True)
class FederationParticipant:
    """
    Stable identity of a federation participant.

    This is deliberately distinct from:
    - hostname
    - network address
    - API endpoint
    - profile name
    - transport connection
    - trust state
    - authorization state
    """

    participant_id: str
    participant_type: FederationParticipantType

    def __post_init__(self) -> None:
        if not isinstance(self.participant_id, str):
            raise TypeError("participant_id must be a string")

        if not self.participant_id.strip():
            raise ValueError("participant_id must not be empty")

        if not isinstance(
            self.participant_type,
            FederationParticipantType,
        ):
            raise TypeError(
                "participant_type must be a FederationParticipantType"
            )


@dataclass(frozen=True)
class FederationPeer:
    """
    A federation participant together with its current federation state.

    Network/discovery metadata is deliberately kept outside the identity
    object. A discovered endpoint does not itself establish trust,
    authentication, authorization, or exchange eligibility.
    """

    participant: FederationParticipant
    state: FederationPeerState

    def __post_init__(self) -> None:
        if not isinstance(self.participant, FederationParticipant):
            raise TypeError(
                "participant must be a FederationParticipant"
            )

        if not isinstance(self.state, FederationPeerState):
            raise TypeError(
                "state must be a FederationPeerState"
            )

    @property
    def participant_id(self) -> str:
        return self.participant.participant_id

    @property
    def participant_type(self) -> FederationParticipantType:
        return self.participant.participant_type

    @property
    def is_exchange_eligible(self) -> bool:
        return self.state is FederationPeerState.EXCHANGE_ELIGIBLE

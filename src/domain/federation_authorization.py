from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.federation_identity import FederationParticipant


class FederationCapability(str, Enum):
    """Explicit capabilities that may be granted to a participant."""

    DISCOVER_PEERS = "DISCOVER_PEERS"
    READ_COLLECTIVE = "READ_COLLECTIVE"
    WRITE_COLLECTIVE = "WRITE_COLLECTIVE"
    REQUEST_KNOWLEDGE = "REQUEST_KNOWLEDGE"
    RECEIVE_KNOWLEDGE = "RECEIVE_KNOWLEDGE"


@dataclass(frozen=True)
class FederationAuthorization:
    """
    Participant-specific federation authorization.

    Authorization is deliberately separate from:
    - discovery
    - trust
    - authentication
    - knowledge adoption
    """

    participant: FederationParticipant
    capabilities: frozenset[FederationCapability]

    @property
    def participant_id(self) -> str:
        return self.participant.participant_id

    def has_capability(
        self,
        capability: FederationCapability,
    ) -> bool:
        if not isinstance(capability, FederationCapability):
            raise TypeError(
                "capability must be a FederationCapability"
            )

        return capability in self.capabilities

    def with_capability(
        self,
        capability: FederationCapability,
    ) -> FederationAuthorization:
        if not isinstance(capability, FederationCapability):
            raise TypeError(
                "capability must be a FederationCapability"
            )

        return FederationAuthorization(
            participant=self.participant,
            capabilities=self.capabilities | frozenset({capability}),
        )

    def without_capability(
        self,
        capability: FederationCapability,
    ) -> FederationAuthorization:
        if not isinstance(capability, FederationCapability):
            raise TypeError(
                "capability must be a FederationCapability"
            )

        return FederationAuthorization(
            participant=self.participant,
            capabilities=self.capabilities - frozenset({capability}),
        )


def authorize_participant(
    *,
    participant: FederationParticipant,
    capabilities: frozenset[FederationCapability] = frozenset(),
) -> FederationAuthorization:
    """Create explicit participant-specific authorization."""

    if not isinstance(participant, FederationParticipant):
        raise TypeError(
            "participant must be a FederationParticipant"
        )

    if not isinstance(capabilities, frozenset):
        raise TypeError(
            "capabilities must be a frozenset"
        )

    if not all(
        isinstance(capability, FederationCapability)
        for capability in capabilities
    ):
        raise TypeError(
            "capabilities must contain only FederationCapability values"
        )

    return FederationAuthorization(
        participant=participant,
        capabilities=capabilities,
    )

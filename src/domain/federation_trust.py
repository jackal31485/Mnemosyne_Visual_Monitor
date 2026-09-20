from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.federation_identity import (
    FederationParticipant,
    FederationPeerState,
)


class FederationTrustState(str, Enum):
    """Explicit trust lifecycle for a federation participant."""

    UNTRUSTED = "UNTRUSTED"
    TRUSTED = "TRUSTED"
    BLOCKED = "BLOCKED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class FederationTrustRecord:
    """
    Explicit trust decision for a federation participant.

    Trust is deliberately separate from:
    - discovery
    - authentication
    - authorization
    - exchange eligibility
    """

    participant: FederationParticipant
    state: FederationTrustState
    established_at: Optional[int] = None
    expires_at: Optional[int] = None
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.participant, FederationParticipant):
            raise TypeError(
                "participant must be a FederationParticipant"
            )

        if not isinstance(self.state, FederationTrustState):
            raise TypeError(
                "state must be a FederationTrustState"
            )

        for field_name, value in (
            ("established_at", self.established_at),
            ("expires_at", self.expires_at),
        ):
            if value is not None and not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer or None"
                )

        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")

        if (
            self.established_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.established_at
        ):
            raise ValueError(
                "expires_at must be later than established_at"
            )

    @property
    def participant_id(self) -> str:
        return self.participant.participant_id

    @property
    def is_trusted(self) -> bool:
        return self.state is FederationTrustState.TRUSTED

    @property
    def is_blocked(self) -> bool:
        return self.state is FederationTrustState.BLOCKED

    @property
    def is_revoked(self) -> bool:
        return self.state is FederationTrustState.REVOKED

    @property
    def is_expired(self) -> bool:
        return self.state is FederationTrustState.EXPIRED

    @property
    def is_exchange_eligible(self) -> bool:
        """
        Trust alone never grants federation exchange eligibility.
        """

        return False

    def expire(self) -> FederationTrustRecord:
        return FederationTrustRecord(
            participant=self.participant,
            state=FederationTrustState.EXPIRED,
            established_at=self.established_at,
            expires_at=self.expires_at,
            reason=self.reason,
        )

    def block(self, reason: Optional[str] = None) -> FederationTrustRecord:
        return FederationTrustRecord(
            participant=self.participant,
            state=FederationTrustState.BLOCKED,
            established_at=self.established_at,
            expires_at=self.expires_at,
            reason=reason,
        )

    def revoke(self, reason: Optional[str] = None) -> FederationTrustRecord:
        return FederationTrustRecord(
            participant=self.participant,
            state=FederationTrustState.REVOKED,
            established_at=self.established_at,
            expires_at=self.expires_at,
            reason=reason,
        )


def establish_federation_trust(
    *,
    participant: FederationParticipant,
    established_at: int,
    expires_at: Optional[int] = None,
    reason: Optional[str] = None,
) -> FederationTrustRecord:
    """
    Explicitly establish trust for a federation participant.

    This operation does not authenticate, authorize, or enable exchange.
    """

    return FederationTrustRecord(
        participant=participant,
        state=FederationTrustState.TRUSTED,
        established_at=established_at,
        expires_at=expires_at,
        reason=reason,
    )


def trust_state_for_peer(
    trust: FederationTrustRecord,
) -> FederationPeerState:
    """
    Map trust state to the existing peer lifecycle without skipping
    authentication or authorization stages.
    """

    if not isinstance(trust, FederationTrustRecord):
        raise TypeError("trust must be a FederationTrustRecord")

    if trust.state is FederationTrustState.BLOCKED:
        return FederationPeerState.BLOCKED

    if trust.state is FederationTrustState.REVOKED:
        return FederationPeerState.REVOKED

    if trust.state is FederationTrustState.EXPIRED:
        return FederationPeerState.EXPIRED

    if trust.state is FederationTrustState.TRUSTED:
        return FederationPeerState.TRUST_ESTABLISHED

    return FederationPeerState.IDENTIFIED

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.federation_identity import FederationParticipant


class FederationSessionState(str, Enum):
    """Authentication state of a federation session."""

    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class FederationSession:
    """
    Authenticated federation session.

    Authentication is deliberately distinct from:
    - discovery
    - trust
    - authorization
    - knowledge exchange

    A session is fail-closed unless it is explicitly authenticated.
    """

    participant: FederationParticipant
    state: FederationSessionState
    session_id: str
    authenticated_at: Optional[int] = None
    expires_at: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.participant, FederationParticipant):
            raise TypeError(
                "participant must be a FederationParticipant"
            )

        if not isinstance(self.state, FederationSessionState):
            raise TypeError(
                "state must be a FederationSessionState"
            )

        if not isinstance(self.session_id, str):
            raise TypeError("session_id must be a string")

        if not self.session_id.strip():
            raise ValueError("session_id must not be empty")

        for field_name, value in (
            ("authenticated_at", self.authenticated_at),
            ("expires_at", self.expires_at),
        ):
            if value is not None and not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer or None"
                )

        if (
            self.authenticated_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.authenticated_at
        ):
            raise ValueError(
                "expires_at must be later than authenticated_at"
            )

    @property
    def participant_id(self) -> str:
        return self.participant.participant_id

    @property
    def is_authenticated(self) -> bool:
        return self.state is FederationSessionState.AUTHENTICATED

    @property
    def permits_communication(self) -> bool:
        """Fail-closed communication gate."""

        return self.is_authenticated

    def expire(self) -> FederationSession:
        return FederationSession(
            participant=self.participant,
            state=FederationSessionState.EXPIRED,
            session_id=self.session_id,
            authenticated_at=self.authenticated_at,
            expires_at=self.expires_at,
        )

    def revoke(self) -> FederationSession:
        return FederationSession(
            participant=self.participant,
            state=FederationSessionState.REVOKED,
            session_id=self.session_id,
            authenticated_at=self.authenticated_at,
            expires_at=self.expires_at,
        )


def authenticate_federation_session(
    *,
    participant: FederationParticipant,
    session_id: str,
    authenticated_at: int,
    expires_at: Optional[int] = None,
) -> FederationSession:
    """Create an explicitly authenticated federation session."""

    return FederationSession(
        participant=participant,
        state=FederationSessionState.AUTHENTICATED,
        session_id=session_id,
        authenticated_at=authenticated_at,
        expires_at=expires_at,
    )


def unauthenticated_federation_session(
    *,
    participant: FederationParticipant,
    session_id: str,
) -> FederationSession:
    """Create a session that is explicitly denied communication."""

    return FederationSession(
        participant=participant,
        state=FederationSessionState.UNAUTHENTICATED,
        session_id=session_id,
    )

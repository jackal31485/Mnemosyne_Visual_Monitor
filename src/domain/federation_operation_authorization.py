"""Phase 17C enforcement boundary for privileged federation operations.

Authentication and capability authorization are deliberately composed here,
rather than embedded in low-level federation data structures or DAOs.

This module does not establish trust, perform authentication, adopt knowledge,
persist data, or mutate authoritative state.
"""

from __future__ import annotations

from .federation_authorization import (
    FederationAuthorization,
    FederationCapability,
)
from .federation_session import FederationSession


def authorize_federation_operation(
    session: FederationSession,
    authorization: FederationAuthorization,
    required_capability: FederationCapability,
) -> None:
    """Authorize one privileged federation operation.

    Fail-closed requirements:
    - the session must be explicitly authenticated;
    - the session must currently permit communication;
    - session and authorization must identify the same participant;
    - the required capability must be explicitly granted.

    Trust, discovery, validation, or network reachability do not substitute
    for authentication or capability authorization.
    """

    if not isinstance(session, FederationSession):
        raise TypeError("session must be a FederationSession")

    if not isinstance(authorization, FederationAuthorization):
        raise TypeError(
            "authorization must be a FederationAuthorization"
        )

    if not isinstance(required_capability, FederationCapability):
        raise TypeError(
            "required_capability must be a FederationCapability"
        )

    if not session.is_authenticated:
        raise PermissionError(
            "federation operation requires an authenticated session"
        )

    if not session.permits_communication:
        raise PermissionError(
            "federation session does not permit communication"
        )

    if session.participant != authorization.participant:
        raise PermissionError(
            "federation session participant does not match authorization"
        )

    if not authorization.has_capability(required_capability):
        raise PermissionError(
            f"missing federation capability: "
            f"{required_capability.value}"
        )


__all__ = ["authorize_federation_operation"]

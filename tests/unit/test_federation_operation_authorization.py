from __future__ import annotations

import pytest

from src.domain.federation_authorization import (
    FederationCapability,
    authorize_participant,
)
from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)
from src.domain.federation_operation_authorization import (
    authorize_federation_operation,
)
from src.domain.federation_session import (
    authenticate_federation_session,
    unauthenticated_federation_session,
)


def _participant(name: str) -> FederationParticipant:
    return FederationParticipant(
        participant_id=name,
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )


def _authenticated(participant: FederationParticipant):
    return authenticate_federation_session(
        participant=participant,
        session_id="session-1",
        authenticated_at=100,
        expires_at=200,
    )


def _authorization(
    participant: FederationParticipant,
    *capabilities: FederationCapability,
):
    return authorize_participant(
        participant=participant,
        capabilities=frozenset(capabilities),
    )


def test_unauthenticated_session_fails_closed() -> None:
    participant = _participant("remote-a")
    session = unauthenticated_federation_session(
        participant=participant,
        session_id="session-1",
    )
    authorization = _authorization(
        participant,
        FederationCapability.RECEIVE_KNOWLEDGE,
    )

    with pytest.raises(PermissionError, match="authenticated session"):
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )


def test_expired_session_fails_closed() -> None:
    participant = _participant("remote-a")
    session = _authenticated(participant).expire()
    authorization = _authorization(
        participant,
        FederationCapability.RECEIVE_KNOWLEDGE,
    )

    with pytest.raises(PermissionError, match="authenticated session"):
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )


def test_revoked_session_fails_closed() -> None:
    participant = _participant("remote-a")
    session = _authenticated(participant).revoke()
    authorization = _authorization(
        participant,
        FederationCapability.RECEIVE_KNOWLEDGE,
    )

    with pytest.raises(PermissionError, match="authenticated session"):
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )


def test_mismatched_participant_fails_closed() -> None:
    session = _authenticated(_participant("remote-a"))
    authorization = _authorization(
        _participant("remote-b"),
        FederationCapability.RECEIVE_KNOWLEDGE,
    )

    with pytest.raises(PermissionError, match="does not match"):
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )


def test_missing_capability_fails_closed() -> None:
    participant = _participant("remote-a")
    session = _authenticated(participant)
    authorization = _authorization(
        participant,
        FederationCapability.REQUEST_KNOWLEDGE,
    )

    with pytest.raises(PermissionError, match="missing federation capability"):
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )


def test_matching_authentication_and_capability_permits_operation() -> None:
    participant = _participant("remote-a")
    session = _authenticated(participant)
    authorization = _authorization(
        participant,
        FederationCapability.RECEIVE_KNOWLEDGE,
    )

    assert (
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )
        is None
    )


def test_trust_or_validation_is_not_represented_as_authorization() -> None:
    participant = _participant("remote-a")
    session = _authenticated(participant)
    authorization = _authorization(participant)

    with pytest.raises(PermissionError, match="missing federation capability"):
        authorize_federation_operation(
            session,
            authorization,
            FederationCapability.RECEIVE_KNOWLEDGE,
        )

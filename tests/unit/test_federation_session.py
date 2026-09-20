import pytest

from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)
from src.domain.federation_session import (
    FederationSessionState,
    authenticate_federation_session,
    unauthenticated_federation_session,
)


@pytest.fixture
def participant():
    return FederationParticipant(
        participant_id="remote-001",
        participant_type=FederationParticipantType.REMOTE_MNEMOSYNE_INSTANCE,
    )


def test_session_can_be_explicitly_authenticated(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-001",
        authenticated_at=100,
        expires_at=200,
    )

    assert session.state is FederationSessionState.AUTHENTICATED
    assert session.is_authenticated is True
    assert session.permits_communication is True


def test_unauthenticated_session_fails_closed(participant):
    session = unauthenticated_federation_session(
        participant=participant,
        session_id="session-001",
    )

    assert session.is_authenticated is False
    assert session.permits_communication is False


def test_expired_session_fails_closed(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-001",
        authenticated_at=100,
        expires_at=200,
    )

    expired = session.expire()

    assert expired.state is FederationSessionState.EXPIRED
    assert expired.is_authenticated is False
    assert expired.permits_communication is False


def test_revoked_session_fails_closed(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-001",
        authenticated_at=100,
    )

    revoked = session.revoke()

    assert revoked.state is FederationSessionState.REVOKED
    assert revoked.is_authenticated is False
    assert revoked.permits_communication is False


def test_expiration_must_follow_authentication(participant):
    with pytest.raises(ValueError):
        authenticate_federation_session(
            participant=participant,
            session_id="session-001",
            authenticated_at=200,
            expires_at=100,
        )


def test_empty_session_id_is_rejected(participant):
    with pytest.raises(ValueError):
        authenticate_federation_session(
            participant=participant,
            session_id="",
            authenticated_at=100,
        )


def test_invalid_session_id_type_is_rejected(participant):
    with pytest.raises(TypeError):
        authenticate_federation_session(
            participant=participant,
            session_id=None,  # type: ignore[arg-type]
            authenticated_at=100,
        )


def test_session_is_immutable(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-001",
        authenticated_at=100,
    )

    with pytest.raises(AttributeError):
        session.state = FederationSessionState.REVOKED  # type: ignore[misc]

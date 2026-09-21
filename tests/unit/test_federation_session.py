import pytest

from src.domain.federation_identity import (
    FederationParticipant,
    FederationParticipantType,
)
from src.domain.federation_session import (
    FederationSessionState,
    authenticate_federation_session,
    unauthenticated_federation_session,
    session_is_active,
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


def test_authenticated_session_is_active_within_valid_interval(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-1",
        authenticated_at=100,
        expires_at=200,
    )

    assert session_is_active(session, at=100) is True
    assert session_is_active(session, at=199) is True


def test_authenticated_session_is_inactive_at_expiration(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-1",
        authenticated_at=100,
        expires_at=200,
    )

    assert session_is_active(session, at=200) is False
    assert session_is_active(session, at=201) is False


def test_authenticated_session_is_inactive_before_authentication(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-1",
        authenticated_at=100,
        expires_at=200,
    )

    assert session_is_active(session, at=99) is False


def test_expired_and_revoked_sessions_are_temporally_inactive(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-1",
        authenticated_at=100,
        expires_at=200,
    )

    assert session_is_active(session.expire(), at=150) is False
    assert session_is_active(session.revoke(), at=150) is False


def test_session_activity_requires_integer_timestamp(participant):
    session = authenticate_federation_session(
        participant=participant,
        session_id="session-1",
        authenticated_at=100,
        expires_at=200,
    )

    with pytest.raises(TypeError, match="at must be an integer"):
        session_is_active(session, at="100")

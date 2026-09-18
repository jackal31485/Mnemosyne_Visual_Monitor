from datetime import datetime, timedelta, timezone

import pytest

from src.domain.transfer_applicability import (
    ApplicabilityDecision,
    ContradictionSignal,
    TransferApplicabilitySignals,
    analyze_transfer_applicability,
)
from src.domain.transfer_authorization import (
    AuthorizationMechanism,
    AuthorizationRequest,
    authorization_is_active,
    authorize_transfer,
)
from src.domain.transfer_candidate_generation import (
    TransferSource,
    generate_transfer_candidate,
)
from src.domain.transfer_contract import TransferStatus


AUTHORIZED_AT = datetime(2026, 9, 18, 20, 0, tzinfo=timezone.utc)


def _candidate():
    source = TransferSource(
        knowledge_id="knowledge-1",
        source_profile="horus",
        evidence_ids=("evidence-1",),
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
        entity_ids=("entity-1",),
        relationship_ids=("relationship-1",),
        temporal_scope=("2026-01",),
    )
    return generate_transfer_candidate(source, "thoth")


def _signals(**overrides):
    values = dict(
        evidence_quality=0.9,
        novelty=0.9,
        entity_overlap=0.8,
        relationship_overlap=0.7,
        temporal_compatibility=0.9,
        destination_knowledge_gap=0.9,
    )
    values.update(overrides)
    return TransferApplicabilitySignals(**values)


def _analysis(candidate=None, **overrides):
    candidate = candidate or _candidate()
    return analyze_transfer_applicability(candidate, _signals(**overrides))


def _request(**overrides):
    values = dict(
        actor="operator",
        scope="knowledge-transfer",
        authorized_at=AUTHORIZED_AT,
        mechanism=AuthorizationMechanism.HUMAN,
    )
    values.update(overrides)
    return AuthorizationRequest(**values)


def test_authorization_requires_explicit_request_and_creates_authorized_record():
    candidate = _candidate()
    analysis = _analysis(candidate)

    authorization, record = authorize_transfer(
        candidate,
        analysis,
        _request(),
    )

    assert authorization.candidate_id == candidate.candidate_id
    assert authorization.source_profile == "horus"
    assert authorization.destination_profile == "thoth"
    assert authorization.actor == "operator"
    assert authorization.scope == "knowledge-transfer"
    assert authorization.revoked is False

    assert record.status is TransferStatus.AUTHORIZED
    assert record.candidate_id == candidate.candidate_id
    assert record.authorization_id == authorization.authorization_id
    assert record.transfer_id == candidate.provenance.transfer_record_id
    assert record.provenance == candidate.provenance


def test_authorization_is_deterministic_for_same_governance_inputs():
    candidate = _candidate()
    analysis = _analysis(candidate)

    first, first_record = authorize_transfer(
        candidate,
        analysis,
        _request(),
    )
    second, second_record = authorize_transfer(
        candidate,
        analysis,
        _request(),
    )

    assert first == second
    assert first_record == second_record


def test_custom_authorization_id_is_preserved():
    candidate = _candidate()

    authorization, record = authorize_transfer(
        candidate,
        _analysis(candidate),
        _request(authorization_id="auth-explicit-1"),
    )

    assert authorization.authorization_id == "auth-explicit-1"
    assert record.authorization_id == "auth-explicit-1"


def test_not_applicable_candidate_cannot_be_authorized():
    candidate = _candidate()
    analysis = _analysis(
        candidate,
        entity_overlap=0.0,
        relationship_overlap=0.0,
        temporal_compatibility=0.0,
        destination_knowledge_gap=0.1,
        novelty=0.1,
        evidence_quality=0.1,
    )

    assert analysis.decision is ApplicabilityDecision.NOT_APPLICABLE

    with pytest.raises(ValueError, match="not-applicable"):
        authorize_transfer(candidate, analysis, _request())


def test_review_required_requires_review_approval_mechanism():
    candidate = _candidate()
    analysis = _analysis(
        candidate,
        contradiction=ContradictionSignal.STRONG,
    )

    assert analysis.decision is ApplicabilityDecision.REVIEW_REQUIRED

    with pytest.raises(ValueError, match="review approval"):
        authorize_transfer(
            candidate,
            analysis,
            _request(mechanism=AuthorizationMechanism.HUMAN),
        )

    authorization, record = authorize_transfer(
        candidate,
        analysis,
        _request(mechanism=AuthorizationMechanism.REVIEW_APPROVAL),
    )

    assert authorization.revoked is False
    assert record.status is TransferStatus.AUTHORIZED


def test_analysis_must_match_candidate():
    candidate = _candidate()
    other_candidate = generate_transfer_candidate(
        TransferSource(
            knowledge_id="knowledge-2",
            source_profile="horus",
            evidence_ids=("evidence-2",),
            source_memory_ids=("memory-2",),
            observation_ids=("observation-2",),
        ),
        "thoth",
    )

    with pytest.raises(ValueError, match="candidate ID"):
        authorize_transfer(
            candidate,
            _analysis(other_candidate),
            _request(),
        )


def test_non_candidate_lifecycle_state_cannot_be_authorized():
    candidate = _candidate().transition_to(TransferStatus.REJECTED)

    with pytest.raises(ValueError, match="only CANDIDATE"):
        authorize_transfer(
            candidate,
            _analysis(_candidate()),
            _request(),
        )


def test_authorization_does_not_mutate_or_adopt_candidate():
    candidate = _candidate()
    analysis = _analysis(candidate)

    authorize_transfer(candidate, analysis, _request())

    assert candidate.status is TransferStatus.CANDIDATE


def test_authorization_does_not_create_adopted_record():
    candidate = _candidate()
    analysis = _analysis(candidate)

    _, record = authorize_transfer(candidate, analysis, _request())

    assert record.status is TransferStatus.AUTHORIZED
    assert record.adopted_at is None


def test_authorization_has_no_raw_memory_content():
    candidate = _candidate()
    analysis = _analysis(candidate)

    authorization, record = authorize_transfer(
        candidate,
        analysis,
        _request(),
    )

    for value in (
        authorization.actor,
        authorization.scope,
        authorization.authorization_id,
        record.transfer_id,
        record.authorization_id,
    ):
        assert "memory-1" not in value
        assert "observation-1" not in value


def test_active_authorization_respects_revocation_and_expiration():
    authorization, _ = authorize_transfer(
        _candidate(),
        _analysis(),
        _request(expires_at=AUTHORIZED_AT + timedelta(hours=1)),
    )

    assert authorization_is_active(
        authorization,
        at=AUTHORIZED_AT,
    )
    assert authorization_is_active(
        authorization,
        at=AUTHORIZED_AT + timedelta(minutes=30),
    )
    assert not authorization_is_active(
        authorization,
        at=AUTHORIZED_AT + timedelta(hours=2),
    )

    revoked = type(authorization)(
        authorization_id=authorization.authorization_id,
        candidate_id=authorization.candidate_id,
        source_profile=authorization.source_profile,
        destination_profile=authorization.destination_profile,
        actor=authorization.actor,
        authorized_at=authorization.authorized_at,
        scope=authorization.scope,
        expires_at=authorization.expires_at,
        revoked=True,
    )

    assert not authorization_is_active(
        revoked,
        at=AUTHORIZED_AT + timedelta(minutes=30),
    )


def test_authorization_is_not_active_before_authorized_at():
    authorization, _ = authorize_transfer(
        _candidate(),
        _analysis(),
        _request(),
    )

    assert not authorization_is_active(
        authorization,
        at=AUTHORIZED_AT - timedelta(seconds=1),
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("actor", ""),
        ("scope", ""),
    ],
)
def test_authorization_request_requires_governance_text(field, value):
    values = dict(
        actor="operator",
        scope="knowledge-transfer",
        authorized_at=AUTHORIZED_AT,
        mechanism=AuthorizationMechanism.HUMAN,
    )
    values[field] = value

    with pytest.raises(ValueError):
        AuthorizationRequest(**values)


def test_authorization_request_rejects_expiration_before_authorization():
    with pytest.raises(ValueError, match="must not precede"):
        AuthorizationRequest(
            actor="operator",
            scope="knowledge-transfer",
            authorized_at=AUTHORIZED_AT,
            expires_at=AUTHORIZED_AT - timedelta(seconds=1),
            mechanism=AuthorizationMechanism.HUMAN,
        )


def test_authorization_request_rejects_invalid_mechanism():
    with pytest.raises(ValueError, match="AuthorizationMechanism"):
        AuthorizationRequest(
            actor="operator",
            scope="knowledge-transfer",
            authorized_at=AUTHORIZED_AT,
            mechanism="automatic",
        )


def test_authorization_rejects_wrong_analysis_type():
    with pytest.raises(
        TypeError,
        match="TransferApplicabilityAnalysis",
    ):
        authorize_transfer(
            _candidate(),
            object(),
            _request(),
        )


def test_authorization_rejects_wrong_request_type():
    with pytest.raises(TypeError, match="AuthorizationRequest"):
        authorize_transfer(
            _candidate(),
            _analysis(),
            object(),
        )


def test_authorization_preserves_provenance_lineage():
    candidate = _candidate()

    _, record = authorize_transfer(
        candidate,
        _analysis(candidate),
        _request(),
    )

    assert record.provenance.source_profile == "horus"
    assert record.provenance.destination_profile == "thoth"
    assert record.provenance.source_knowledge_id == "knowledge-1"
    assert record.provenance.evidence_ids == ("evidence-1",)
    assert record.provenance.source_memory_ids == ("memory-1",)
    assert record.provenance.observation_ids == ("observation-1",)


def test_authorization_scope_is_explicit():
    authorization, _ = authorize_transfer(
        _candidate(),
        _analysis(),
        _request(scope="specific-knowledge-transfer"),
    )

    assert authorization.scope == "specific-knowledge-transfer"

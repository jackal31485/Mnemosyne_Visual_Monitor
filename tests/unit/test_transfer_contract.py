"""Phase 14A tests for the governed cross-profile transfer contract."""

from datetime import datetime, timedelta, timezone

import pytest

from src.domain.transfer_contract import (
    TransferAuthorization,
    TransferCandidate,
    TransferProvenance,
    TransferRecord,
    TransferStatus,
)


NOW = datetime(2026, 9, 18, 16, 0, tzinfo=timezone.utc)


def make_provenance(**overrides):
    values = dict(
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        transfer_candidate_id="tc-001",
        transfer_record_id="tr-001",
        evidence_ids=("ev-1", "ev-2"),
        source_memory_ids=("mem-1", "mem-2"),
        observation_ids=("obs-1", "obs-2"),
        mental_model_id="mm-001",
        derivation_method="phase-14a-transfer-contract",
    )
    values.update(overrides)
    return TransferProvenance(**values)


def make_candidate(**overrides):
    values = dict(
        candidate_id="tc-001",
        source_profile="jeeves",
        destination_profile="boss",
        source_knowledge_id="knowledge-001",
        proposed_applicability="destination lacks current knowledge",
        provenance=make_provenance(),
        supporting_evidence_ids=("ev-1", "ev-2"),
        source_memory_ids=("mem-1", "mem-2"),
        observation_ids=("obs-1", "obs-2"),
        mental_model_id="mm-001",
        entity_ids=("entity-sqlite",),
        relationship_ids=("rel-authoritative",),
        temporal_scope=("current",),
        benefit_signals=("destination_gap", "novelty"),
        contradiction_state="none",
        created_at=NOW,
    )
    values.update(overrides)
    return TransferCandidate(**values)


def test_candidate_is_explicitly_not_adoption():
    candidate = make_candidate()
    assert candidate.status is TransferStatus.CANDIDATE

    with pytest.raises(ValueError, match="may only represent CANDIDATE"):
        make_candidate(status=TransferStatus.ADOPTED)


def test_candidate_preserves_source_and_destination_identity():
    candidate = make_candidate()
    assert candidate.source_profile == "jeeves"
    assert candidate.destination_profile == "boss"
    assert candidate.source_profile != candidate.destination_profile


def test_provenance_contains_no_raw_content_and_preserves_identifiers():
    provenance = make_provenance()
    assert provenance.source_memory_ids == ("mem-1", "mem-2")
    assert provenance.evidence_ids == ("ev-1", "ev-2")
    assert not hasattr(provenance, "content")
    assert not hasattr(provenance, "raw_memory")


def test_provenance_ids_must_match_candidate():
    bad = make_provenance(transfer_candidate_id="tc-other")
    with pytest.raises(ValueError, match="candidate ID"):
        make_candidate(provenance=bad)


def test_candidate_requires_evidence():
    with pytest.raises(ValueError, match="at least one identifier"):
        make_provenance(evidence_ids=())


def test_cross_profile_transfer_is_required():
    with pytest.raises(ValueError, match="must differ"):
        make_candidate(
            source_profile="jeeves",
            destination_profile="jeeves",
            provenance=make_provenance(destination_profile="jeeves"),
        )


def test_candidate_lifecycle_allows_rejection_and_revocation_but_not_implicit_adoption():
    candidate = make_candidate()
    rejected = candidate.transition_to(TransferStatus.REJECTED)
    assert rejected.status is TransferStatus.REJECTED

    with pytest.raises(ValueError, match="invalid transfer transition"):
        candidate.transition_to(TransferStatus.STALE)

    with pytest.raises(ValueError, match="authorization and adoption"):
        candidate.transition_to(TransferStatus.AUTHORIZED)


def test_candidate_is_immutable():
    candidate = make_candidate()
    with pytest.raises((AttributeError, TypeError)):
        candidate.destination_profile = "hawk"


def test_authorization_is_explicit_and_bound_to_profiles():
    authorization = TransferAuthorization(
        authorization_id="auth-001",
        candidate_id="tc-001",
        source_profile="jeeves",
        destination_profile="boss",
        actor="operator",
        authorized_at=NOW,
        scope="knowledge-001",
        expires_at=NOW + timedelta(hours=1),
    )
    assert authorization.is_active is True
    assert authorization.candidate_id == "tc-001"


def test_authorization_cannot_cross_bind_same_profile():
    with pytest.raises(ValueError, match="must differ"):
        TransferAuthorization(
            authorization_id="auth-001",
            candidate_id="tc-001",
            source_profile="jeeves",
            destination_profile="jeeves",
            actor="operator",
            authorized_at=NOW,
            scope="knowledge-001",
        )


def test_expired_at_cannot_precede_authorization():
    with pytest.raises(ValueError, match="precede"):
        TransferAuthorization(
            authorization_id="auth-001",
            candidate_id="tc-001",
            source_profile="jeeves",
            destination_profile="boss",
            actor="operator",
            authorized_at=NOW,
            scope="knowledge-001",
            expires_at=NOW - timedelta(seconds=1),
        )


def test_transfer_record_requires_matching_provenance():
    provenance = make_provenance(transfer_record_id="tr-999")
    with pytest.raises(ValueError, match="transfer record ID"):
        TransferRecord(
            transfer_id="tr-001",
            candidate_id="tc-001",
            authorization_id="auth-001",
            provenance=provenance,
            created_at=NOW,
        )


def test_adopted_transfer_record_requires_adoption_timestamp():
    with pytest.raises(ValueError, match="adopted_at"):
        TransferRecord(
            transfer_id="tr-001",
            candidate_id="tc-001",
            authorization_id="auth-001",
            provenance=make_provenance(),
            created_at=NOW,
            status=TransferStatus.ADOPTED,
        )


def test_adopted_transfer_record_preserves_audit_identity():
    record = TransferRecord(
        transfer_id="tr-001",
        candidate_id="tc-001",
        authorization_id="auth-001",
        provenance=make_provenance(),
        created_at=NOW,
        adopted_at=NOW + timedelta(minutes=2),
        status=TransferStatus.ADOPTED,
    )
    assert record.status is TransferStatus.ADOPTED
    assert record.transfer_id == "tr-001"
    assert record.version == 1

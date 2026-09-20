from datetime import datetime, timezone

import pytest

from src.domain.federation_audit import (
    FederationAuditEventKind,
    FederationAuditRecord,
)
from src.domain.federation_diagnostics import (
    FederationDiagnostics,
    build_federation_diagnostics,
)


NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)


def make_record(
    audit_id: str,
    kind: FederationAuditEventKind,
    *,
    participant_id: str = "node-a",
    outcome: str = "accepted",
) -> FederationAuditRecord:
    return FederationAuditRecord(
        audit_id=audit_id,
        event_kind=kind,
        occurred_at=NOW,
        actor_id=participant_id,
        participant_id=participant_id,
        outcome=outcome,
    )


def test_empty_diagnostics_are_healthy():
    snapshot = build_federation_diagnostics(())

    assert snapshot.total_events == 0
    assert snapshot.event_counts == ()
    assert snapshot.outcome_counts == ()
    assert snapshot.participant_counts == ()
    assert snapshot.attributable_events == 0
    assert snapshot.audit_healthy is True


def test_diagnostics_count_lifecycle_activity():
    records = (
        make_record("a1", FederationAuditEventKind.DISCOVERY),
        make_record("a2", FederationAuditEventKind.EXCHANGE),
        make_record("a3", FederationAuditEventKind.EXCHANGE),
        make_record(
            "a4",
            FederationAuditEventKind.SYNCHRONIZATION,
            outcome="duplicate",
        ),
        make_record("a5", FederationAuditEventKind.CONFLICT),
        make_record("a6", FederationAuditEventKind.REVOCATION),
        make_record("a7", FederationAuditEventKind.ADOPTION),
        make_record("a8", FederationAuditEventKind.PROJECTION),
    )

    snapshot = build_federation_diagnostics(records)

    assert snapshot.total_events == 8
    assert snapshot.exchange_events == 2
    assert snapshot.synchronization_events == 1
    assert snapshot.conflict_events == 1
    assert snapshot.revocation_events == 1
    assert snapshot.adoption_events == 1
    assert snapshot.projection_events == 1


def test_counts_are_deterministic():
    records = (
        make_record(
            "b",
            FederationAuditEventKind.EXCHANGE,
            participant_id="node-b",
            outcome="accepted",
        ),
        make_record(
            "a",
            FederationAuditEventKind.EXCHANGE,
            participant_id="node-a",
            outcome="rejected",
        ),
        make_record(
            "c",
            FederationAuditEventKind.CONFLICT,
            participant_id="node-a",
            outcome="open",
        ),
    )

    snapshot = build_federation_diagnostics(records)

    assert snapshot.event_counts == (
        ("conflict", 1),
        ("exchange", 2),
    )
    assert snapshot.outcome_counts == (
        ("accepted", 1),
        ("open", 1),
        ("rejected", 1),
    )
    assert snapshot.participant_counts == (
        ("node-a", 2),
        ("node-b", 1),
    )


def test_conflicts_and_revocations_remain_visible():
    records = (
        make_record("a1", FederationAuditEventKind.CONFLICT),
        make_record("a2", FederationAuditEventKind.REVOCATION),
    )

    snapshot = build_federation_diagnostics(records)

    assert snapshot.conflicts_visible is True
    assert snapshot.revocations_visible is True


def test_all_events_are_attributable():
    records = (
        make_record("a1", FederationAuditEventKind.TRUST),
        make_record("a2", FederationAuditEventKind.AUTHORIZATION),
        make_record("a3", FederationAuditEventKind.EXCHANGE),
    )

    snapshot = build_federation_diagnostics(records)

    assert snapshot.attributable_events == 3
    assert snapshot.audit_healthy is True


def test_diagnostics_reject_non_audit_records():
    with pytest.raises(TypeError):
        build_federation_diagnostics([object()])


def test_diagnostics_facade_is_read_only():
    records = (
        make_record("a1", FederationAuditEventKind.EXCHANGE),
    )
    diagnostics = FederationDiagnostics(records)

    assert diagnostics.records() == records
    assert diagnostics.snapshot().total_events == 1

    with pytest.raises(AttributeError):
        diagnostics._records = ()


def test_diagnostics_snapshot_is_immutable():
    snapshot = build_federation_diagnostics(
        [make_record("a1", FederationAuditEventKind.REVOCATION)]
    )

    with pytest.raises(AttributeError):
        snapshot.total_events = 99


def test_diagnostics_contains_no_raw_memory_payload():
    snapshot = build_federation_diagnostics(
        [make_record("a1", FederationAuditEventKind.EXCHANGE)]
    )

    assert not hasattr(snapshot, "payload")
    assert not hasattr(snapshot, "raw_memory")

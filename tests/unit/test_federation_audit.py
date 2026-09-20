from datetime import datetime, timezone

import pytest

from src.domain.federation_audit import (
    FederationAuditError,
    FederationAuditEventKind,
    FederationAuditRecord,
    FederationAuditStore,
)


def make_record(**overrides):
    values = {
        "audit_id": "audit-1",
        "event_kind": FederationAuditEventKind.REVOCATION,
        "occurred_at": datetime(2026, 9, 20, tzinfo=timezone.utc),
        "actor_id": "remote-node",
        "participant_id": "remote-node",
        "outcome": "propagated",
        "exchange_id": "exchange-1",
        "transfer_id": "transfer-1",
        "candidate_id": "candidate-1",
        "authorization_id": "auth-1",
        "learned_id": "learned-1",
        "source_profile": "remote-profile",
        "destination_profile": "local-profile",
    }
    values.update(overrides)
    return FederationAuditRecord(**values)


def test_audit_record_is_immutable():
    record = make_record()

    with pytest.raises(AttributeError):
        record.outcome = "changed"


def test_audit_record_requires_attribution():
    with pytest.raises(FederationAuditError):
        make_record(actor_id="")

    with pytest.raises(FederationAuditError):
        make_record(participant_id="")


def test_audit_record_rejects_same_profiles():
    with pytest.raises(FederationAuditError):
        make_record(
            source_profile="same",
            destination_profile="same",
        )


def test_audit_record_normalizes_details():
    record = make_record(details=(("z", "last"), ("a", "first")))

    assert record.details == (("a", "first"), ("z", "last"))


def test_audit_record_rejects_duplicate_detail_keys():
    with pytest.raises(FederationAuditError):
        make_record(details=(("key", "one"), ("key", "two")))


def test_store_is_append_only(tmp_path):
    store = FederationAuditStore(tmp_path)
    record = make_record()

    store.append(record)

    with pytest.raises(FederationAuditError):
        store.append(record)


def test_store_round_trips_record(tmp_path):
    store = FederationAuditStore(tmp_path)
    record = make_record(details=(("reason", "source_revoked"),))

    store.append(record)

    assert store.list_records() == (record,)


def test_store_preserves_multiple_events(tmp_path):
    store = FederationAuditStore(tmp_path)

    first = make_record(
        audit_id="audit-1",
        event_kind=FederationAuditEventKind.EXCHANGE,
    )
    second = make_record(
        audit_id="audit-2",
        event_kind=FederationAuditEventKind.CONFLICT,
        outcome="visible",
    )

    store.append(second)
    store.append(first)

    assert tuple(record.audit_id for record in store.list_records()) == (
        "audit-1",
        "audit-2",
    )


def test_audit_record_contains_no_raw_memory_payload():
    record = make_record(details=(("source_memory_id", "memory-1"),))

    assert not hasattr(record, "payload")
    assert not hasattr(record, "raw_memory")
    assert record.details == (("source_memory_id", "memory-1"),)

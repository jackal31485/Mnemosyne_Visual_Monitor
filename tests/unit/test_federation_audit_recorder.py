from datetime import datetime, timezone

import pytest

from src.domain.federation_audit import (
    FederationAuditError,
    FederationAuditEventKind,
    FederationAuditStore,
)
from src.domain.federation_audit_recorder import FederationAuditRecorder


NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)


def make_recorder(tmp_path):
    return FederationAuditRecorder(
        FederationAuditStore(tmp_path),
        actor_id="local-node",
    )


def test_recorder_appends_governed_event(tmp_path):
    recorder = make_recorder(tmp_path)

    record = recorder.record(
        FederationAuditEventKind.EXCHANGE,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="validated",
        event_key="exchange-001",
        exchange_id="exchange-001",
    )

    assert record.event_kind is FederationAuditEventKind.EXCHANGE
    assert record.actor_id == "local-node"
    assert record.participant_id == "remote-node"
    assert record.exchange_id == "exchange-001"

    stored = recorder._store.list_records()
    assert stored == (record,)


def test_audit_id_is_deterministic(tmp_path):
    recorder = make_recorder(tmp_path)

    first = recorder.record(
        FederationAuditEventKind.TRUST,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="trusted",
        event_key="participant-001",
    )

    assert first.audit_id.startswith("federation-audit-")

    with pytest.raises(FederationAuditError):
        recorder.record(
            FederationAuditEventKind.TRUST,
            participant_id="remote-node",
            occurred_at=NOW,
            outcome="trusted",
            event_key="participant-001",
        )


def test_different_event_kinds_do_not_share_audit_identity(tmp_path):
    recorder = make_recorder(tmp_path)

    trust = recorder.record(
        FederationAuditEventKind.TRUST,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="trusted",
        event_key="same-key",
    )

    auth = recorder.record(
        FederationAuditEventKind.AUTHENTICATION,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="authenticated",
        event_key="same-key",
    )

    assert trust.audit_id != auth.audit_id


def test_recorder_preserves_federation_identifiers(tmp_path):
    recorder = make_recorder(tmp_path)

    record = recorder.record(
        FederationAuditEventKind.ADOPTION,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="proposed",
        event_key="candidate-001",
        exchange_id="exchange-001",
        transfer_id="transfer-001",
        candidate_id="candidate-001",
        authorization_id="authorization-001",
        learned_id="learned-001",
        source_profile="remote-profile",
        destination_profile="local-profile",
        details=(
            ("status", "proposed"),
            ("mechanism", "phase-14"),
        ),
    )

    assert record.exchange_id == "exchange-001"
    assert record.transfer_id == "transfer-001"
    assert record.candidate_id == "candidate-001"
    assert record.authorization_id == "authorization-001"
    assert record.learned_id == "learned-001"
    assert record.source_profile == "remote-profile"
    assert record.destination_profile == "local-profile"
    assert record.details == (
        ("mechanism", "phase-14"),
        ("status", "proposed"),
    )


def test_recorder_never_accepts_raw_memory_payload_field(tmp_path):
    recorder = make_recorder(tmp_path)

    record = recorder.record(
        FederationAuditEventKind.EXCHANGE,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="validated",
        event_key="exchange-002",
        exchange_id="exchange-002",
    )

    assert not hasattr(record, "payload")
    assert not hasattr(record, "raw_memory")
    assert not hasattr(record, "memory_content")


def test_recorder_rejects_invalid_actor(tmp_path):
    with pytest.raises(ValueError):
        FederationAuditRecorder(
            FederationAuditStore(tmp_path),
            actor_id="",
        )


def test_recorder_rejects_invalid_event_key(tmp_path):
    recorder = make_recorder(tmp_path)

    with pytest.raises(ValueError):
        recorder.record(
            FederationAuditEventKind.DISCOVERY,
            participant_id="remote-node",
            occurred_at=NOW,
            outcome="discovered",
            event_key="",
        )

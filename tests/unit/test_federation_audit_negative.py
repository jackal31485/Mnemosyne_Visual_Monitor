"""Phase 16K negative federation audit boundary coverage."""

import json
from datetime import datetime, timezone

import pytest

from src.domain.federation_audit import (
    FederationAuditError,
    FederationAuditEventKind,
    FederationAuditRecord,
    FederationAuditStore,
)
from src.domain.federation_audit_recorder import FederationAuditRecorder


NOW = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)


def _record(**overrides):
    values = {
        "audit_id": "audit-negative-1",
        "event_kind": FederationAuditEventKind.EXCHANGE,
        "occurred_at": NOW,
        "actor_id": "local-node",
        "participant_id": "remote-node",
        "outcome": "validated",
        "exchange_id": "exchange-negative-1",
        "source_profile": "remote-profile",
        "destination_profile": "local-profile",
    }
    values.update(overrides)
    return FederationAuditRecord(**values)


def test_persisted_audit_contains_metadata_only(tmp_path):
    store = FederationAuditStore(tmp_path)

    store.append(
        _record(
            details=(
                ("source_memory_id", "memory-1"),
                ("status", "validated"),
            )
        )
    )

    files = list(store.base.glob("*.json"))
    assert len(files) == 1

    payload = json.loads(files[0].read_text(encoding="utf-8"))

    assert payload["exchange_id"] == "exchange-negative-1"
    assert payload["source_profile"] == "remote-profile"
    assert payload["destination_profile"] == "local-profile"
    assert "payload" not in payload
    assert "raw_memory" not in payload
    assert "memory_content" not in payload
    assert "content" not in payload


def test_audit_store_has_no_update_or_delete_authority(tmp_path):
    store = FederationAuditStore(tmp_path)

    assert not hasattr(store, "update")
    assert not hasattr(store, "replace")
    assert not hasattr(store, "delete")
    assert not hasattr(store, "remove")
    assert not hasattr(store, "clear")

    record = _record()
    store.append(record)

    with pytest.raises(FederationAuditError):
        store.append(record)

    assert store.list_records() == (record,)


def test_audit_record_cannot_be_mutated_after_recording(tmp_path):
    recorder = FederationAuditRecorder(
        FederationAuditStore(tmp_path),
        actor_id="local-node",
    )

    record = recorder.record(
        FederationAuditEventKind.AUTHORIZATION,
        participant_id="remote-node",
        occurred_at=NOW,
        outcome="observed",
        event_key="authorization-negative-1",
    )

    with pytest.raises(AttributeError):
        record.outcome = "authorized"

    assert recorder._store.list_records() == (record,)


def test_invalid_audit_attribution_fails_closed(tmp_path):
    store = FederationAuditStore(tmp_path)

    with pytest.raises(FederationAuditError):
        store.append(
            _record(
                actor_id="",
            )
        )

    with pytest.raises(FederationAuditError):
        store.append(
            _record(
                participant_id="",
            )
        )

    assert store.list_records() == ()

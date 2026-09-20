"""Phase 16K federation audit records and append-only storage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class FederationAuditEventKind(str, Enum):
    DISCOVERY = "discovery"
    TRUST = "trust"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    EXCHANGE = "exchange"
    SYNCHRONIZATION = "synchronization"
    CONFLICT = "conflict"
    ADOPTION = "adoption"
    PROJECTION = "projection"
    REVOCATION = "revocation"


class FederationAuditError(ValueError):
    """Raised when a federation audit operation violates its contract."""


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FederationAuditError(f"{name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class FederationAuditRecord:
    """Immutable, attributable federation lifecycle audit event."""

    audit_id: str
    event_kind: FederationAuditEventKind
    occurred_at: datetime
    actor_id: str
    participant_id: str
    outcome: str
    peer_id: str | None = None
    exchange_id: str | None = None
    transfer_id: str | None = None
    candidate_id: str | None = None
    authorization_id: str | None = None
    learned_id: str | None = None
    source_profile: str | None = None
    destination_profile: str | None = None
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "audit_id",
            "actor_id",
            "participant_id",
            "outcome",
        ):
            object.__setattr__(
                self,
                name,
                _required_text(name, getattr(self, name)),
            )

        if not isinstance(self.event_kind, FederationAuditEventKind):
            raise TypeError(
                "event_kind must be FederationAuditEventKind"
            )

        if not isinstance(self.occurred_at, datetime):
            raise TypeError("occurred_at must be a datetime")

        optional_names = (
            "peer_id",
            "exchange_id",
            "transfer_id",
            "candidate_id",
            "authorization_id",
            "learned_id",
            "source_profile",
            "destination_profile",
        )

        for name in optional_names:
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _required_text(name, value),
                )

        if (
            self.source_profile is not None
            and self.destination_profile is not None
            and self.source_profile == self.destination_profile
        ):
            raise FederationAuditError(
                "source and destination profiles must differ"
            )

        if isinstance(self.details, (str, bytes)):
            raise TypeError("details must be an iterable of key/value pairs")

        normalized_details: list[tuple[str, str]] = []
        for key, value in self.details:
            normalized_details.append(
                (
                    _required_text("detail key", key),
                    _required_text("detail value", value),
                )
            )

        if len(normalized_details) != len(
            {key for key, _ in normalized_details}
        ):
            raise FederationAuditError(
                "details must not contain duplicate keys"
            )

        object.__setattr__(
            self,
            "details",
            tuple(sorted(normalized_details)),
        )


class FederationAuditStore:
    """Append-only local federation audit store."""

    def __init__(self, base_path: Path) -> None:
        self.base = Path(base_path) / "federation_audit"
        self.base.mkdir(parents=True, exist_ok=True)

    def append(self, record: FederationAuditRecord) -> None:
        if not isinstance(record, FederationAuditRecord):
            raise TypeError("record must be a FederationAuditRecord")

        path = self.base / f"{record.audit_id}.json"
        if path.exists():
            raise FederationAuditError(
                "audit history is immutable; audit ID already exists"
            )

        payload = {
            "audit_id": record.audit_id,
            "event_kind": record.event_kind.value,
            "occurred_at": record.occurred_at.isoformat(),
            "actor_id": record.actor_id,
            "participant_id": record.participant_id,
            "outcome": record.outcome,
            "peer_id": record.peer_id,
            "exchange_id": record.exchange_id,
            "transfer_id": record.transfer_id,
            "candidate_id": record.candidate_id,
            "authorization_id": record.authorization_id,
            "learned_id": record.learned_id,
            "source_profile": record.source_profile,
            "destination_profile": record.destination_profile,
            "details": dict(record.details),
        }

        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def list_records(self) -> tuple[FederationAuditRecord, ...]:
        """Return stored records in deterministic audit-ID order."""
        records: list[FederationAuditRecord] = []

        for path in sorted(self.base.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(
                FederationAuditRecord(
                    audit_id=payload["audit_id"],
                    event_kind=FederationAuditEventKind(
                        payload["event_kind"]
                    ),
                    occurred_at=datetime.fromisoformat(
                        payload["occurred_at"]
                    ),
                    actor_id=payload["actor_id"],
                    participant_id=payload["participant_id"],
                    outcome=payload["outcome"],
                    peer_id=payload.get("peer_id"),
                    exchange_id=payload.get("exchange_id"),
                    transfer_id=payload.get("transfer_id"),
                    candidate_id=payload.get("candidate_id"),
                    authorization_id=payload.get("authorization_id"),
                    learned_id=payload.get("learned_id"),
                    source_profile=payload.get("source_profile"),
                    destination_profile=payload.get("destination_profile"),
                    details=tuple(
                        sorted(payload.get("details", {}).items())
                    ),
                )
            )

        return tuple(records)


__all__ = [
    "FederationAuditError",
    "FederationAuditEventKind",
    "FederationAuditRecord",
    "FederationAuditStore",
]

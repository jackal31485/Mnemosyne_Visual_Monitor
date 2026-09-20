"""Phase 16K federation lifecycle audit recorder.

This module is an observational adapter around existing federation domain
operations. It records governed lifecycle metadata without becoming an
authorization, adoption, revocation, synchronization, or persistence
authority.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from .federation_audit import (
    FederationAuditEventKind,
    FederationAuditRecord,
    FederationAuditStore,
)


class FederationAuditRecorder:
    """Create and persist immutable federation lifecycle audit records."""

    def __init__(
        self,
        store: FederationAuditStore,
        *,
        actor_id: str,
    ) -> None:
        if not isinstance(store, FederationAuditStore):
            raise TypeError("store must be a FederationAuditStore")

        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("actor_id must be non-empty text")

        self._store = store
        self._actor_id = actor_id.strip()

    @staticmethod
    def _audit_id(
        event_kind: FederationAuditEventKind,
        *,
        event_key: str,
    ) -> str:
        material = f"{event_kind.value}|{event_key}"
        digest = sha256(material.encode("utf-8")).hexdigest()[:20]
        return f"federation-audit-{digest}"

    def record(
        self,
        event_kind: FederationAuditEventKind,
        *,
        participant_id: str,
        occurred_at: datetime,
        outcome: str,
        event_key: str,
        peer_id: str | None = None,
        exchange_id: str | None = None,
        transfer_id: str | None = None,
        candidate_id: str | None = None,
        authorization_id: str | None = None,
        learned_id: str | None = None,
        source_profile: str | None = None,
        destination_profile: str | None = None,
        details: tuple[tuple[str, str], ...] = (),
    ) -> FederationAuditRecord:
        """Create and append one governed federation audit event."""

        if not isinstance(event_kind, FederationAuditEventKind):
            raise TypeError(
                "event_kind must be FederationAuditEventKind"
            )

        if not isinstance(occurred_at, datetime):
            raise TypeError("occurred_at must be a datetime")

        if not isinstance(event_key, str) or not event_key.strip():
            raise ValueError("event_key must be non-empty text")

        record = FederationAuditRecord(
            audit_id=self._audit_id(
                event_kind,
                event_key=event_key.strip(),
            ),
            event_kind=event_kind,
            occurred_at=occurred_at,
            actor_id=self._actor_id,
            participant_id=participant_id,
            outcome=outcome,
            peer_id=peer_id,
            exchange_id=exchange_id,
            transfer_id=transfer_id,
            candidate_id=candidate_id,
            authorization_id=authorization_id,
            learned_id=learned_id,
            source_profile=source_profile,
            destination_profile=destination_profile,
            details=details,
        )

        self._store.append(record)
        return record


__all__ = ["FederationAuditRecorder"]

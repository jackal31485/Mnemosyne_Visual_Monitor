"""Phase 16K observational diagnostics for federation activity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .federation_audit import (
    FederationAuditEventKind,
    FederationAuditRecord,
)


@dataclass(frozen=True, slots=True)
class FederationDiagnosticSnapshot:
    """Immutable observational snapshot of federation audit activity."""

    total_events: int
    event_counts: tuple[tuple[str, int], ...]
    outcome_counts: tuple[tuple[str, int], ...]
    participant_counts: tuple[tuple[str, int], ...]
    exchange_events: int
    synchronization_events: int
    conflict_events: int
    revocation_events: int
    adoption_events: int
    projection_events: int
    attributable_events: int
    audit_healthy: bool

    @property
    def conflicts_visible(self) -> bool:
        """Whether conflict activity remains represented in diagnostics."""
        return self.conflict_events > 0

    @property
    def revocations_visible(self) -> bool:
        """Whether revocation activity remains represented in diagnostics."""
        return self.revocation_events > 0


def _counts(values: Iterable[str]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}

    for value in values:
        counts[value] = counts.get(value, 0) + 1

    return tuple(sorted(counts.items()))


def build_federation_diagnostics(
    records: Iterable[FederationAuditRecord],
) -> FederationDiagnosticSnapshot:
    """Build an observational snapshot from immutable audit records.

    This function never mutates, authorizes, adopts, revokes, or persists
    federation state. It consumes audit metadata only.
    """
    record_list = tuple(records)

    if any(
        not isinstance(record, FederationAuditRecord)
        for record in record_list
    ):
        raise TypeError(
            "records must contain only FederationAuditRecord instances"
        )

    event_values = [record.event_kind.value for record in record_list]
    outcome_values = [record.outcome for record in record_list]
    participant_values = [record.participant_id for record in record_list]

    def event_count(kind: FederationAuditEventKind) -> int:
        return sum(record.event_kind is kind for record in record_list)

    attributable_events = sum(
        bool(record.actor_id.strip() and record.participant_id.strip())
        for record in record_list
    )

    return FederationDiagnosticSnapshot(
        total_events=len(record_list),
        event_counts=_counts(event_values),
        outcome_counts=_counts(outcome_values),
        participant_counts=_counts(participant_values),
        exchange_events=event_count(FederationAuditEventKind.EXCHANGE),
        synchronization_events=event_count(
            FederationAuditEventKind.SYNCHRONIZATION
        ),
        conflict_events=event_count(FederationAuditEventKind.CONFLICT),
        revocation_events=event_count(FederationAuditEventKind.REVOCATION),
        adoption_events=event_count(FederationAuditEventKind.ADOPTION),
        projection_events=event_count(FederationAuditEventKind.PROJECTION),
        attributable_events=attributable_events,
        audit_healthy=(
            attributable_events == len(record_list)
            and len({record.audit_id for record in record_list})
            == len(record_list)
        ),
    )


@dataclass(frozen=True, slots=True)
class FederationDiagnostics:
    """Read-only diagnostics facade over supplied federation audit records."""

    _records: tuple[FederationAuditRecord, ...]

    def __init__(
        self,
        records: Iterable[FederationAuditRecord],
    ) -> None:
        normalized = tuple(records)

        if any(
            not isinstance(record, FederationAuditRecord)
            for record in normalized
        ):
            raise TypeError(
                "records must contain only FederationAuditRecord instances"
            )

        object.__setattr__(self, "_records", normalized)

    def snapshot(self) -> FederationDiagnosticSnapshot:
        """Return a fresh immutable diagnostic snapshot."""
        return build_federation_diagnostics(self._records)

    def records(self) -> tuple[FederationAuditRecord, ...]:
        """Return the immutable diagnostic input history."""
        return self._records


__all__ = [
    "FederationDiagnosticSnapshot",
    "FederationDiagnostics",
    "build_federation_diagnostics",
]

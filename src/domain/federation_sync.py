from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FederationSyncStatus(str, Enum):
    """Outcome of synchronization processing."""

    APPLIED = "APPLIED"
    DUPLICATE = "DUPLICATE"
    RETRY = "RETRY"
    DIVERGED = "DIVERGED"


@dataclass(frozen=True)
class FederationCheckpoint:
    """Immutable synchronization checkpoint for one participant."""

    participant_id: str
    sequence: int
    version: int

    def __post_init__(self) -> None:
        if not isinstance(self.participant_id, str):
            raise TypeError("participant_id must be a string")

        if not self.participant_id.strip():
            raise ValueError("participant_id must not be empty")

        if not isinstance(self.sequence, int):
            raise TypeError("sequence must be an integer")

        if self.sequence < 0:
            raise ValueError("sequence must not be negative")

        if not isinstance(self.version, int):
            raise TypeError("version must be an integer")

        if self.version < 0:
            raise ValueError("version must not be negative")


@dataclass(frozen=True)
class FederationSyncRecord:
    """
    Immutable record of a synchronization attempt.

    Exchange IDs are retained so repeated delivery can be recognized
    without applying the same exchange twice.
    """

    exchange_id: str
    participant_id: str
    sequence: int
    version: int
    status: FederationSyncStatus
    retry_count: int = 0
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("exchange_id", self.exchange_id),
            ("participant_id", self.participant_id),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")

            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        for field_name, value in (
            ("sequence", self.sequence),
            ("version", self.version),
            ("retry_count", self.retry_count),
        ):
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")

        if self.sequence < 0:
            raise ValueError("sequence must not be negative")

        if self.version < 0:
            raise ValueError("version must not be negative")

        if self.retry_count < 0:
            raise ValueError("retry_count must not be negative")

        if not isinstance(self.status, FederationSyncStatus):
            raise TypeError(
                "status must be a FederationSyncStatus"
            )

        if self.reason is not None and not isinstance(
            self.reason,
            str,
        ):
            raise TypeError("reason must be a string or None")

    @property
    def is_diverged(self) -> bool:
        return self.status is FederationSyncStatus.DIVERGED

    @property
    def is_duplicate(self) -> bool:
        return self.status is FederationSyncStatus.DUPLICATE


@dataclass(frozen=True)
class FederationSyncDecision:
    """Decision made before applying a synchronized exchange."""

    status: FederationSyncStatus
    checkpoint: FederationCheckpoint
    reason: Optional[str] = None

    @property
    def should_apply(self) -> bool:
        return self.status is FederationSyncStatus.APPLIED

    @property
    def requires_retry(self) -> bool:
        return self.status is FederationSyncStatus.RETRY

    @property
    def is_duplicate(self) -> bool:
        return self.status is FederationSyncStatus.DUPLICATE

    @property
    def is_diverged(self) -> bool:
        return self.status is FederationSyncStatus.DIVERGED


def evaluate_synchronization(
    *,
    checkpoint: FederationCheckpoint,
    exchange_id: str,
    sequence: int,
    version: int,
    seen_exchange_ids: frozenset[str] = frozenset(),
) -> FederationSyncDecision:
    """
    Determine whether an exchange may advance synchronization.

    Rules:
    - previously seen exchange IDs are duplicates;
    - a gap in sequence requires retry;
    - an older version is a duplicate/stale delivery;
    - a newer version without a contiguous sequence is visible as
      divergence rather than silently reconciled;
    - only the exact next sequence may be applied.
    """

    if not isinstance(checkpoint, FederationCheckpoint):
        raise TypeError(
            "checkpoint must be a FederationCheckpoint"
        )

    if not isinstance(exchange_id, str):
        raise TypeError("exchange_id must be a string")

    if not exchange_id.strip():
        raise ValueError("exchange_id must not be empty")

    if not isinstance(sequence, int):
        raise TypeError("sequence must be an integer")

    if not isinstance(version, int):
        raise TypeError("version must be an integer")

    if sequence < 0:
        raise ValueError("sequence must not be negative")

    if version < 0:
        raise ValueError("version must not be negative")

    if not isinstance(seen_exchange_ids, frozenset):
        raise TypeError(
            "seen_exchange_ids must be a frozenset"
        )

    if exchange_id in seen_exchange_ids:
        return FederationSyncDecision(
            status=FederationSyncStatus.DUPLICATE,
            checkpoint=checkpoint,
            reason="exchange already processed",
        )

    expected_sequence = checkpoint.sequence + 1

    if sequence < expected_sequence:
        return FederationSyncDecision(
            status=FederationSyncStatus.DUPLICATE,
            checkpoint=checkpoint,
            reason="stale sequence",
        )

    if sequence > expected_sequence:
        return FederationSyncDecision(
            status=FederationSyncStatus.RETRY,
            checkpoint=checkpoint,
            reason="sequence gap",
        )

    if version < checkpoint.version:
        return FederationSyncDecision(
            status=FederationSyncStatus.DUPLICATE,
            checkpoint=checkpoint,
            reason="stale version",
        )

    if version > checkpoint.version + 1:
        return FederationSyncDecision(
            status=FederationSyncStatus.DIVERGED,
            checkpoint=checkpoint,
            reason="version divergence",
        )

    return FederationSyncDecision(
        status=FederationSyncStatus.APPLIED,
        checkpoint=FederationCheckpoint(
            participant_id=checkpoint.participant_id,
            sequence=sequence,
            version=version,
        ),
    )


def record_retry(
    *,
    exchange_id: str,
    participant_id: str,
    sequence: int,
    version: int,
    retry_count: int,
    reason: str,
) -> FederationSyncRecord:
    """Record a retry without changing the synchronization checkpoint."""

    return FederationSyncRecord(
        exchange_id=exchange_id,
        participant_id=participant_id,
        sequence=sequence,
        version=version,
        status=FederationSyncStatus.RETRY,
        retry_count=retry_count,
        reason=reason,
    )

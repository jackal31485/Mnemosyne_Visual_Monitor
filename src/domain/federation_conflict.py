from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FederationConflictKind(str, Enum):
    """Types of attributable federation conflict."""

    VERSION = "VERSION"
    CONTENT = "CONTENT"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"


class FederationConflictState(str, Enum):
    """Visibility lifecycle of a federation conflict."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class FederationConflict:
    """
    Immutable, attributable federation conflict record.

    A conflict records competing exchange/source evidence. It does not
    select a winner or mutate either source.
    """

    conflict_id: str
    kind: FederationConflictKind
    state: FederationConflictState
    participant_ids: tuple[str, ...]
    exchange_ids: tuple[str, ...]
    source_memory_ids: tuple[str, ...]
    description: str
    resolution: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("conflict_id", self.conflict_id),
            ("description", self.description),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")

            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if not isinstance(self.kind, FederationConflictKind):
            raise TypeError(
                "kind must be a FederationConflictKind"
            )

        if not isinstance(self.state, FederationConflictState):
            raise TypeError(
                "state must be a FederationConflictState"
            )

        for field_name, values in (
            ("participant_ids", self.participant_ids),
            ("exchange_ids", self.exchange_ids),
            ("source_memory_ids", self.source_memory_ids),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not values:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

            if not all(
                isinstance(value, str) and value.strip()
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain non-empty strings"
                )

        if self.resolution is not None and not isinstance(
            self.resolution,
            str,
        ):
            raise TypeError(
                "resolution must be a string or None"
            )

        if (
            self.state is FederationConflictState.RESOLVED
            and not self.resolution
        ):
            raise ValueError(
                "resolved conflicts require a resolution"
            )

    @property
    def is_open(self) -> bool:
        return self.state is FederationConflictState.OPEN

    @property
    def is_resolved(self) -> bool:
        return self.state is FederationConflictState.RESOLVED

    @property
    def is_attributable(self) -> bool:
        return bool(
            self.participant_ids
            and self.exchange_ids
            and self.source_memory_ids
        )

    def acknowledge(self) -> FederationConflict:
        """Make the conflict explicitly acknowledged without resolving it."""

        return FederationConflict(
            conflict_id=self.conflict_id,
            kind=self.kind,
            state=FederationConflictState.ACKNOWLEDGED,
            participant_ids=self.participant_ids,
            exchange_ids=self.exchange_ids,
            source_memory_ids=self.source_memory_ids,
            description=self.description,
            resolution=self.resolution,
        )

    def resolve(
        self,
        resolution: str,
    ) -> FederationConflict:
        """
        Record an explicit resolution.

        Resolution is an explicit later action; conflict creation never
        performs it automatically.
        """

        if not isinstance(resolution, str):
            raise TypeError("resolution must be a string")

        if not resolution.strip():
            raise ValueError("resolution must not be empty")

        return FederationConflict(
            conflict_id=self.conflict_id,
            kind=self.kind,
            state=FederationConflictState.RESOLVED,
            participant_ids=self.participant_ids,
            exchange_ids=self.exchange_ids,
            source_memory_ids=self.source_memory_ids,
            description=self.description,
            resolution=resolution,
        )


def detect_federation_conflict(
    *,
    conflict_id: str,
    kind: FederationConflictKind,
    participant_ids: tuple[str, ...],
    exchange_ids: tuple[str, ...],
    source_memory_ids: tuple[str, ...],
    description: str,
) -> FederationConflict:
    """
    Record a newly detected conflict.

    Detection is deliberately non-resolving: the resulting record remains
    OPEN until an explicit later action acknowledges or resolves it.
    """

    return FederationConflict(
        conflict_id=conflict_id,
        kind=kind,
        state=FederationConflictState.OPEN,
        participant_ids=participant_ids,
        exchange_ids=exchange_ids,
        source_memory_ids=source_memory_ids,
        description=description,
    )

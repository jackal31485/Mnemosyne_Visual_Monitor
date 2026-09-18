"""Read-only Phase 14 cross-profile transfer projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.domain.transfer_adoption import DestinationLearnedRepresentation
from src.domain.transfer_contract import (
    TransferAuthorization,
    TransferCandidate,
    TransferRecord,
)
from src.domain.transfer_revocation import (
    RevokedDestinationLearnedState,
    TransferRevocation,
)


@dataclass(frozen=True, slots=True)
class TransferLearningState:
    """Immutable read-only state supplied to the API projection."""

    candidates: tuple[TransferCandidate, ...] = ()
    authorizations: tuple[TransferAuthorization, ...] = ()
    records: tuple[TransferRecord, ...] = ()
    adoptions: tuple[DestinationLearnedRepresentation, ...] = ()
    revoked_states: tuple[RevokedDestinationLearnedState, ...] = ()
    revocations: tuple[TransferRevocation, ...] = ()


class TransferLearningProjection:
    """Read-only projection over governed Phase 14 state."""

    def __init__(
        self,
        state: TransferLearningState | None = None,
    ) -> None:
        self._state = state or TransferLearningState()

    @property
    def state(self) -> TransferLearningState:
        return self._state

    def list_transfers(
        self,
        *,
        source_profile: str | None = None,
        destination_profile: str | None = None,
    ) -> list[TransferRecord]:
        records = self._state.records

        if source_profile is not None:
            records = tuple(
                record
                for record in records
                if record.provenance.source_profile == source_profile
            )

        if destination_profile is not None:
            records = tuple(
                record
                for record in records
                if record.provenance.destination_profile == destination_profile
            )

        return list(records)

    def get_transfer(self, transfer_id: str) -> TransferRecord | None:
        return next(
            (
                record
                for record in self._state.records
                if record.transfer_id == transfer_id
            ),
            None,
        )

    def get_candidate(
        self,
        candidate_id: str,
    ) -> TransferCandidate | None:
        return next(
            (
                candidate
                for candidate in self._state.candidates
                if candidate.candidate_id == candidate_id
            ),
            None,
        )

    def get_authorization(
        self,
        authorization_id: str,
    ) -> TransferAuthorization | None:
        return next(
            (
                authorization
                for authorization in self._state.authorizations
                if authorization.authorization_id == authorization_id
            ),
            None,
        )

    def get_adoption(
        self,
        transfer_id: str,
    ) -> DestinationLearnedRepresentation | None:
        return next(
            (
                adoption
                for adoption in self._state.adoptions
                if adoption.transfer_id == transfer_id
            ),
            None,
        )

    def get_revoked_state(
        self,
        transfer_id: str,
    ) -> RevokedDestinationLearnedState | None:
        return next(
            (
                state
                for state in self._state.revoked_states
                if state.transfer_id == transfer_id
            ),
            None,
        )

    def get_revocation(
        self,
        transfer_id: str,
    ) -> TransferRevocation | None:
        return next(
            (
                revocation
                for revocation in self._state.revocations
                if revocation.transfer_id == transfer_id
            ),
            None,
        )


def get_transfer_learning_projection() -> TransferLearningProjection:
    """Return the application's read-only Phase 14 projection."""
    return TransferLearningProjection()


__all__ = [
    "TransferLearningProjection",
    "TransferLearningState",
    "get_transfer_learning_projection",
]

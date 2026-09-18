"""Phase 14G cross-profile transfer revocation and rollback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .mental_model import MentalModel, MentalModelStatus
from .transfer_adoption import DestinationLearnedRepresentation
from .transfer_contract import (
    TransferAuthorization,
    TransferRecord,
    TransferStatus,
)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


class TransferRevocationReason(str, Enum):
    SOURCE_DEPENDENCY_REVOKED = "source_dependency_revoked"
    AUTHORIZATION_REVOKED = "authorization_revoked"
    EXPLICIT_ROLLBACK = "explicit_rollback"


@dataclass(frozen=True, slots=True)
class TransferRevocation:
    """Immutable audit event withdrawing an adopted transfer."""

    transfer_id: str
    candidate_id: str
    authorization_id: str
    learned_id: str
    source_profile: str
    destination_profile: str
    reason: TransferRevocationReason
    revoked_at: datetime
    dependency_ids: tuple[str, ...] = ()
    rollback: bool = False
    derivation_method: str = "phase-14g-transfer-revocation"

    def __post_init__(self) -> None:
        for name in (
            "transfer_id",
            "candidate_id",
            "authorization_id",
            "learned_id",
            "source_profile",
            "destination_profile",
            "derivation_method",
        ):
            _required_text(name, getattr(self, name))

        if not isinstance(self.reason, TransferRevocationReason):
            raise TypeError("reason must be TransferRevocationReason")

        if not isinstance(self.revoked_at, datetime):
            raise TypeError("revoked_at must be a datetime")

        if not isinstance(self.dependency_ids, tuple):
            object.__setattr__(
                self,
                "dependency_ids",
                tuple(self.dependency_ids),
            )

        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.dependency_ids
        ):
            raise ValueError(
                "dependency_ids must contain non-empty identifiers"
            )

        if len(self.dependency_ids) != len(set(self.dependency_ids)):
            raise ValueError("dependency_ids cannot contain duplicates")

        if not isinstance(self.rollback, bool):
            raise TypeError("rollback must be bool")

        if self.source_profile == self.destination_profile:
            raise ValueError("source and destination profiles must differ")


@dataclass(frozen=True, slots=True)
class RevokedDestinationLearnedState:
    """Immutable effective state showing withdrawn destination learning."""

    learned_id: str
    transfer_id: str
    candidate_id: str
    authorization_id: str
    source_profile: str
    destination_profile: str
    source_knowledge_id: str
    source_memory_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    temporal_scope: tuple[str, ...]
    adopted_at: datetime
    revoked_at: datetime
    version: int
    derivation_method: str
    revocation_reason: TransferRevocationReason

    @property
    def status(self) -> TransferStatus:
        return TransferStatus.REVOKED

    @property
    def is_currently_retrievable(self) -> bool:
        return False

    def __post_init__(self) -> None:
        for name in (
            "learned_id",
            "transfer_id",
            "candidate_id",
            "authorization_id",
            "source_profile",
            "destination_profile",
            "source_knowledge_id",
            "derivation_method",
        ):
            _required_text(name, getattr(self, name))

        if self.source_profile == self.destination_profile:
            raise ValueError("source and destination profiles must differ")

        for name in (
            "source_memory_ids",
            "observation_ids",
            "evidence_ids",
            "temporal_scope",
        ):
            values = getattr(self, name)
            if not isinstance(values, tuple):
                object.__setattr__(self, name, tuple(values))

        if not self.evidence_ids:
            raise ValueError("revoked state requires evidence provenance")

        if not isinstance(self.adopted_at, datetime):
            raise TypeError("adopted_at must be a datetime")

        if not isinstance(self.revoked_at, datetime):
            raise TypeError("revoked_at must be a datetime")

        if self.revoked_at < self.adopted_at:
            raise ValueError("revoked_at cannot precede adopted_at")

        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")

        if not isinstance(
            self.revocation_reason,
            TransferRevocationReason,
        ):
            raise TypeError(
                "revocation_reason must be TransferRevocationReason"
            )


@dataclass(frozen=True, slots=True)
class TransferRollbackResult:
    """Immutable result of withdrawing an adopted transfer."""

    revocation: TransferRevocation
    previous_record: TransferRecord
    revoked_record: TransferRecord
    previous_representation: DestinationLearnedRepresentation
    revoked_representation: RevokedDestinationLearnedState
    mental_model: MentalModel | None

    @property
    def transfer_id(self) -> str:
        return self.revocation.transfer_id

    @property
    def is_revoked(self) -> bool:
        return (
            self.revoked_record.status is TransferStatus.REVOKED
            and not self.revoked_representation.is_currently_retrievable
        )


def revoke_transfer(
    record: TransferRecord,
    representation: DestinationLearnedRepresentation,
    authorization: TransferAuthorization,
    *,
    revoked_at: datetime,
    reason: TransferRevocationReason,
    mental_model: MentalModel | None = None,
    dependency_ids: tuple[str, ...] = (),
    rollback: bool = False,
) -> TransferRollbackResult:
    """Withdraw an adopted transfer without mutating its history."""

    if not isinstance(record, TransferRecord):
        raise TypeError("record must be a TransferRecord")

    if not isinstance(
        representation,
        DestinationLearnedRepresentation,
    ):
        raise TypeError(
            "representation must be DestinationLearnedRepresentation"
        )

    if not isinstance(authorization, TransferAuthorization):
        raise TypeError(
            "authorization must be TransferAuthorization"
        )

    if not isinstance(reason, TransferRevocationReason):
        raise TypeError(
            "reason must be TransferRevocationReason"
        )

    if not isinstance(revoked_at, datetime):
        raise TypeError("revoked_at must be a datetime")

    if record.status is not TransferStatus.ADOPTED:
        raise ValueError("only adopted transfer records can be revoked")

    if representation.status is not TransferStatus.ADOPTED:
        raise ValueError(
            "only adopted learned representations can be revoked"
        )

    if record.transfer_id != representation.transfer_id:
        raise ValueError(
            "transfer record and learned representation do not match"
        )

    if record.authorization_id != authorization.authorization_id:
        raise ValueError(
            "transfer record and authorization do not match"
        )

    if record.candidate_id != representation.candidate_id:
        raise ValueError(
            "transfer record and learned representation candidate do not match"
        )

    if record.provenance.source_profile != representation.source_profile:
        raise ValueError("source profile provenance does not match")

    if (
        record.provenance.destination_profile
        != representation.destination_profile
    ):
        raise ValueError("destination profile provenance does not match")

    if representation.authorization_id != authorization.authorization_id:
        raise ValueError(
            "learned representation and authorization do not match"
        )

    if reason is TransferRevocationReason.AUTHORIZATION_REVOKED:
        if not authorization.revoked:
            raise ValueError(
                "authorization revocation requires a revoked authorization"
            )

    if reason is TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED:
        if mental_model is None:
            raise ValueError(
                "source dependency revocation requires a revoked mental model"
            )

        if not isinstance(mental_model, MentalModel):
            raise TypeError("mental_model must be MentalModel or None")

        if mental_model.status is not MentalModelStatus.REVOKED:
            raise ValueError(
                "source dependency revocation requires a revoked mental model"
            )

        if representation.mental_model is not None:
            if mental_model.model_id != representation.mental_model.model_id:
                raise ValueError(
                    "mental model does not match learned representation"
                )

    if reason is TransferRevocationReason.EXPLICIT_ROLLBACK and not rollback:
        raise ValueError(
            "explicit rollback requires rollback=True"
        )

    if rollback and reason is not TransferRevocationReason.EXPLICIT_ROLLBACK:
        raise ValueError(
            "rollback=True requires explicit rollback reason"
        )

    if not isinstance(dependency_ids, tuple):
        dependency_ids = tuple(dependency_ids)

    if any(
        not isinstance(value, str) or not value.strip()
        for value in dependency_ids
    ):
        raise ValueError(
            "dependency_ids must contain non-empty identifiers"
        )

    if len(dependency_ids) != len(set(dependency_ids)):
        raise ValueError("dependency_ids cannot contain duplicates")

    if (
        reason is TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED
        and not dependency_ids
    ):
        raise ValueError(
            "source dependency revocation requires dependency_ids"
        )

    revoked_record = TransferRecord(
        transfer_id=record.transfer_id,
        candidate_id=record.candidate_id,
        authorization_id=record.authorization_id,
        provenance=record.provenance,
        created_at=record.created_at,
        adopted_at=record.adopted_at,
        version=record.version,
        status=TransferStatus.REVOKED,
    )

    revoked_representation = RevokedDestinationLearnedState(
        learned_id=representation.learned_id,
        transfer_id=representation.transfer_id,
        candidate_id=representation.candidate_id,
        authorization_id=representation.authorization_id,
        source_profile=representation.source_profile,
        destination_profile=representation.destination_profile,
        source_knowledge_id=representation.source_knowledge_id,
        source_memory_ids=representation.source_memory_ids,
        observation_ids=representation.observation_ids,
        evidence_ids=representation.evidence_ids,
        temporal_scope=representation.temporal_scope,
        adopted_at=representation.adopted_at,
        revoked_at=revoked_at,
        version=representation.version,
        derivation_method=representation.derivation_method,
        revocation_reason=reason,
    )

    revocation = TransferRevocation(
        transfer_id=record.transfer_id,
        candidate_id=record.candidate_id,
        authorization_id=record.authorization_id,
        learned_id=representation.learned_id,
        source_profile=representation.source_profile,
        destination_profile=representation.destination_profile,
        reason=reason,
        revoked_at=revoked_at,
        dependency_ids=dependency_ids,
        rollback=rollback,
    )

    return TransferRollbackResult(
        revocation=revocation,
        previous_record=record,
        revoked_record=revoked_record,
        previous_representation=representation,
        revoked_representation=revoked_representation,
        mental_model=mental_model,
    )


__all__ = [
    "RevokedDestinationLearnedState",
    "TransferRevocation",
    "TransferRevocationReason",
    "TransferRollbackResult",
    "revoke_transfer",
]

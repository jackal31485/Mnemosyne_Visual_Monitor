"""Phase 16J federation revocation propagation.

Federation revocation is an attributable signal, not a second revocation
lifecycle. Once a remote revocation is received and its lineage is verified,
the existing Phase 14 ``revoke_transfer`` operation remains the sole authority
for withdrawing an adopted destination representation.

No historical record is mutated and no raw private memory content crosses the
federation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .federation_exchange import FederationKnowledgeReceipt
from .federation_identity import FederationParticipant
from .transfer_adoption import DestinationLearnedRepresentation
from .transfer_authorization import TransferAuthorization
from .transfer_contract import TransferRecord
from .transfer_revocation import (
    TransferRevocationReason,
    TransferRollbackResult,
    revoke_transfer,
)
from .mental_model import MentalModel


class FederationRevocationError(ValueError):
    """Raised when a federation revocation signal cannot be propagated."""


@dataclass(frozen=True, slots=True)
class FederationRevocationSignal:
    """Immutable attributable signal requesting downstream revocation."""

    revocation_id: str
    source_participant_id: str
    source_profile: str
    destination_profile: str
    transfer_id: str
    candidate_id: str
    authorization_id: str
    learned_id: str
    source_knowledge_id: str
    source_memory_ids: tuple[str, ...]
    reason: TransferRevocationReason
    revoked_at: datetime
    dependency_ids: tuple[str, ...] = ()
    originating_exchange_id: str = ""

    def __post_init__(self) -> None:
        for name in (
            "revocation_id",
            "source_participant_id",
            "source_profile",
            "destination_profile",
            "transfer_id",
            "candidate_id",
            "authorization_id",
            "learned_id",
            "source_knowledge_id",
            "originating_exchange_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())

        if self.source_profile == self.destination_profile:
            raise ValueError("source and destination profiles must differ")

        if not isinstance(self.reason, TransferRevocationReason):
            raise TypeError("reason must be TransferRevocationReason")

        if not isinstance(self.revoked_at, datetime):
            raise TypeError("revoked_at must be a datetime")

        for name in ("source_memory_ids", "dependency_ids"):
            values = getattr(self, name)
            if isinstance(values, (str, bytes)):
                raise TypeError(
                    f"{name} must be an iterable of identifiers, not text"
                )

            normalized = tuple(value.strip() for value in values)
            if any(not value for value in normalized):
                raise ValueError(f"{name} must contain non-empty text")
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{name} must not contain duplicates")

            object.__setattr__(self, name, tuple(sorted(normalized)))

        if self.reason is TransferRevocationReason.SOURCE_DEPENDENCY_REVOKED:
            if not self.dependency_ids:
                raise ValueError(
                    "source dependency revocation requires dependency_ids"
                )


@dataclass(frozen=True, slots=True)
class FederationRevocationPropagation:
    """Immutable result linking the federation signal to Phase 14 withdrawal."""

    signal: FederationRevocationSignal
    result: TransferRollbackResult

    @property
    def is_revoked(self) -> bool:
        return self.result.is_revoked


def propagate_federation_revocation(
    signal: FederationRevocationSignal,
    *,
    receipt: FederationKnowledgeReceipt,
    recipient: FederationParticipant,
    record: TransferRecord,
    representation: DestinationLearnedRepresentation,
    authorization: TransferAuthorization,
    mental_model: MentalModel | None = None,
) -> FederationRevocationPropagation:
    """Verify a remote revocation and delegate withdrawal to Phase 14."""

    if not isinstance(signal, FederationRevocationSignal):
        raise TypeError("signal must be a FederationRevocationSignal")

    if not isinstance(receipt, FederationKnowledgeReceipt):
        raise TypeError("receipt must be a FederationKnowledgeReceipt")

    if not isinstance(recipient, FederationParticipant):
        raise TypeError("recipient must be a FederationParticipant")

    if not receipt.is_validated:
        raise FederationRevocationError(
            "only validated federation receipts may propagate revocation"
        )

    if receipt.recipient.participant_id != recipient.participant_id:
        raise FederationRevocationError(
            "receipt recipient does not match propagation recipient"
        )

    if (
        receipt.provenance.source_participant_id
        != signal.source_participant_id
    ):
        raise FederationRevocationError(
            "revocation source participant does not match receipt provenance"
        )

    if receipt.provenance.originating_exchange_id != signal.originating_exchange_id:
        raise FederationRevocationError(
            "revocation exchange does not match receipt provenance"
        )

    if signal.destination_profile != record.provenance.destination_profile:
        raise FederationRevocationError(
            "destination profile does not match transfer record"
        )

    if signal.source_profile != record.provenance.source_profile:
        raise FederationRevocationError(
            "source profile does not match transfer record"
        )

    if signal.transfer_id != record.transfer_id:
        raise FederationRevocationError(
            "transfer ID does not match transfer record"
        )

    if signal.candidate_id != record.candidate_id:
        raise FederationRevocationError(
            "candidate ID does not match transfer record"
        )

    if signal.authorization_id != record.authorization_id:
        raise FederationRevocationError(
            "authorization ID does not match transfer record"
        )

    if signal.learned_id != representation.learned_id:
        raise FederationRevocationError(
            "learned ID does not match destination representation"
        )

    if signal.transfer_id != representation.transfer_id:
        raise FederationRevocationError(
            "transfer ID does not match destination representation"
        )

    if signal.source_knowledge_id != representation.source_knowledge_id:
        raise FederationRevocationError(
            "source knowledge ID does not match destination representation"
        )

    if tuple(signal.source_memory_ids) != tuple(
        representation.source_memory_ids
    ):
        raise FederationRevocationError(
            "source memory provenance does not match destination representation"
        )

    result = revoke_transfer(
        record,
        representation,
        authorization,
        revoked_at=signal.revoked_at,
        reason=signal.reason,
        mental_model=mental_model,
        dependency_ids=signal.dependency_ids,
        rollback=(
            signal.reason is TransferRevocationReason.EXPLICIT_ROLLBACK
        ),
    )

    return FederationRevocationPropagation(
        signal=signal,
        result=result,
    )


__all__ = [
    "FederationRevocationError",
    "FederationRevocationPropagation",
    "FederationRevocationSignal",
    "propagate_federation_revocation",
]

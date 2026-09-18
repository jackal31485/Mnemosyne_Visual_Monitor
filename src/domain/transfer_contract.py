"""Phase 14A contracts for governed cross-profile transfer.

These immutable contracts model the transfer boundary without performing a
transfer.  They carry identifiers and governance metadata only; raw private
memory content is intentionally not represented.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Iterable


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _identifiers(name: str, values: Iterable[str], *, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of identifiers, not text")
    materialized = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in materialized):
        raise ValueError(f"{name} must contain non-empty text")
    normalized = tuple(value.strip() for value in materialized)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    result = tuple(sorted(normalized))
    if required and not result:
        raise ValueError(f"{name} must contain at least one identifier")
    return result


class TransferStatus(str, Enum):
    """Governed Phase 14 transfer lifecycle states."""

    AVAILABLE = "available"
    ELIGIBLE = "eligible"
    CANDIDATE = "candidate"
    AUTHORIZED = "authorized"
    ADOPTED = "adopted"
    STALE = "stale"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    REJECTED = "rejected"


_ALLOWED_TRANSITIONS: dict[TransferStatus, frozenset[TransferStatus]] = {
    TransferStatus.AVAILABLE: frozenset({TransferStatus.ELIGIBLE}),
    TransferStatus.ELIGIBLE: frozenset({TransferStatus.CANDIDATE, TransferStatus.REJECTED}),
    TransferStatus.CANDIDATE: frozenset({TransferStatus.AUTHORIZED, TransferStatus.REJECTED, TransferStatus.REVOKED}),
    TransferStatus.AUTHORIZED: frozenset({TransferStatus.ADOPTED, TransferStatus.REJECTED, TransferStatus.REVOKED}),
    TransferStatus.ADOPTED: frozenset({TransferStatus.STALE, TransferStatus.SUPERSEDED, TransferStatus.REVOKED}),
    TransferStatus.STALE: frozenset({TransferStatus.ADOPTED, TransferStatus.SUPERSEDED, TransferStatus.REVOKED}),
    TransferStatus.SUPERSEDED: frozenset(),
    TransferStatus.REVOKED: frozenset(),
    TransferStatus.REJECTED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class TransferProvenance:
    """Source-to-transfer lineage without copying source content."""

    source_profile: str
    destination_profile: str
    source_knowledge_id: str
    transfer_candidate_id: str
    transfer_record_id: str
    evidence_ids: tuple[str, ...]
    source_memory_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    mental_model_id: str | None = None
    derivation_method: str = "phase-14-transfer"

    def __post_init__(self) -> None:
        for name in (
            "source_profile",
            "destination_profile",
            "source_knowledge_id",
            "transfer_candidate_id",
            "transfer_record_id",
            "derivation_method",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        if self.source_profile == self.destination_profile:
            raise ValueError("source_profile and destination_profile must differ")
        object.__setattr__(self, "evidence_ids", _identifiers("evidence_ids", self.evidence_ids, required=True))
        object.__setattr__(self, "source_memory_ids", _identifiers("source_memory_ids", self.source_memory_ids))
        object.__setattr__(self, "observation_ids", _identifiers("observation_ids", self.observation_ids))
        if self.mental_model_id is not None:
            object.__setattr__(self, "mental_model_id", _required_text("mental_model_id", self.mental_model_id))


@dataclass(frozen=True, slots=True)
class TransferCandidate:
    """Immutable proposal for a source-to-destination transfer.

    A candidate is not authorization and does not imply destination adoption.
    """

    candidate_id: str
    source_profile: str
    destination_profile: str
    source_knowledge_id: str
    proposed_applicability: str
    provenance: TransferProvenance
    supporting_evidence_ids: tuple[str, ...]
    source_memory_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    mental_model_id: str | None = None
    entity_ids: tuple[str, ...] = ()
    relationship_ids: tuple[str, ...] = ()
    temporal_scope: tuple[str, ...] = ()
    benefit_signals: tuple[str, ...] = ()
    contradiction_state: str = "none"
    created_at: datetime | None = None
    status: TransferStatus = TransferStatus.CANDIDATE

    def __post_init__(self) -> None:
        for name in (
            "candidate_id",
            "source_profile",
            "destination_profile",
            "source_knowledge_id",
            "proposed_applicability",
            "contradiction_state",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        if self.source_profile == self.destination_profile:
            raise ValueError("source_profile and destination_profile must differ")
        if not isinstance(self.provenance, TransferProvenance):
            raise TypeError("provenance must be a TransferProvenance")
        if self.provenance.transfer_candidate_id != self.candidate_id:
            raise ValueError("provenance candidate ID must match candidate_id")
        if self.provenance.source_profile != self.source_profile:
            raise ValueError("provenance source profile must match candidate")
        if self.provenance.destination_profile != self.destination_profile:
            raise ValueError("provenance destination profile must match candidate")
        if self.provenance.source_knowledge_id != self.source_knowledge_id:
            raise ValueError("provenance knowledge ID must match candidate")
        object.__setattr__(self, "supporting_evidence_ids", _identifiers("supporting_evidence_ids", self.supporting_evidence_ids, required=True))
        object.__setattr__(self, "source_memory_ids", _identifiers("source_memory_ids", self.source_memory_ids))
        object.__setattr__(self, "observation_ids", _identifiers("observation_ids", self.observation_ids))
        object.__setattr__(self, "entity_ids", _identifiers("entity_ids", self.entity_ids))
        object.__setattr__(self, "relationship_ids", _identifiers("relationship_ids", self.relationship_ids))
        object.__setattr__(self, "temporal_scope", _identifiers("temporal_scope", self.temporal_scope))
        object.__setattr__(self, "benefit_signals", _identifiers("benefit_signals", self.benefit_signals))
        if tuple(self.supporting_evidence_ids) != self.provenance.evidence_ids:
            raise ValueError("provenance evidence IDs must match candidate evidence")
        if tuple(self.source_memory_ids) != self.provenance.source_memory_ids:
            raise ValueError("provenance memory IDs must match candidate memories")
        if tuple(self.observation_ids) != self.provenance.observation_ids:
            raise ValueError("provenance observation IDs must match candidate observations")
        if self.mental_model_id != self.provenance.mental_model_id:
            raise ValueError("provenance mental-model ID must match candidate")
        if not isinstance(self.status, TransferStatus):
            try:
                object.__setattr__(self, "status", TransferStatus(self.status))
            except (TypeError, ValueError) as exc:
                raise ValueError("status must be a valid TransferStatus") from exc
        if self.status not in {
            TransferStatus.CANDIDATE,
            TransferStatus.REJECTED,
            TransferStatus.REVOKED,
        }:
            raise ValueError(
                "transfer candidate records may only represent CANDIDATE, "
                "REJECTED, or REVOKED states"
            )
        if self.created_at is not None and not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime or None")

    def can_transition_to(self, new_status: TransferStatus) -> bool:
        """Return whether a lifecycle transition is explicitly allowed."""
        if not isinstance(new_status, TransferStatus):
            raise TypeError("new_status must be a TransferStatus")
        return new_status in _ALLOWED_TRANSITIONS[self.status]

    def transition_to(self, new_status: TransferStatus) -> "TransferCandidate":
        """Return a new candidate with the requested governed state.

        This method is intentionally restricted to states that remain a
        candidate record. Authorization/adoption records are created by later
        Phase 14 stages rather than being implied here.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(f"invalid transfer transition: {self.status.value} -> {new_status.value}")
        if new_status is TransferStatus.AUTHORIZED or new_status is TransferStatus.ADOPTED:
            raise ValueError("authorization and adoption require explicit Phase 14 records")
        return replace(self, status=new_status)


@dataclass(frozen=True, slots=True)
class TransferAuthorization:
    """Explicit permission for one transfer candidate."""

    authorization_id: str
    candidate_id: str
    source_profile: str
    destination_profile: str
    actor: str
    authorized_at: datetime
    scope: str
    expires_at: datetime | None = None
    revoked: bool = False

    def __post_init__(self) -> None:
        for name in (
            "authorization_id",
            "candidate_id",
            "source_profile",
            "destination_profile",
            "actor",
            "scope",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        if self.source_profile == self.destination_profile:
            raise ValueError("source_profile and destination_profile must differ")
        if not isinstance(self.authorized_at, datetime):
            raise TypeError("authorized_at must be a datetime")
        if self.expires_at is not None:
            if not isinstance(self.expires_at, datetime):
                raise TypeError("expires_at must be a datetime or None")
            if self.expires_at < self.authorized_at:
                raise ValueError("expires_at must not precede authorized_at")
        if not isinstance(self.revoked, bool):
            raise TypeError("revoked must be a bool")

    @property
    def is_active(self) -> bool:
        """Whether this authorization is currently usable by governance."""
        return not self.revoked


@dataclass(frozen=True, slots=True)
class TransferRecord:
    """Immutable audit identity for a transfer lifecycle."""

    transfer_id: str
    candidate_id: str
    authorization_id: str
    provenance: TransferProvenance
    created_at: datetime
    adopted_at: datetime | None = None
    version: int = 1
    status: TransferStatus = TransferStatus.AUTHORIZED

    def __post_init__(self) -> None:
        for name in ("transfer_id", "candidate_id", "authorization_id"):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))
        if not isinstance(self.provenance, TransferProvenance):
            raise TypeError("provenance must be a TransferProvenance")
        if self.provenance.transfer_record_id != self.transfer_id:
            raise ValueError("provenance transfer record ID must match transfer_id")
        if self.provenance.transfer_candidate_id != self.candidate_id:
            raise ValueError("provenance candidate ID must match transfer record")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        if self.adopted_at is not None:
            if not isinstance(self.adopted_at, datetime):
                raise TypeError("adopted_at must be a datetime or None")
            if self.adopted_at < self.created_at:
                raise ValueError("adopted_at must not precede created_at")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValueError("version must be a positive integer")
        if not isinstance(self.status, TransferStatus):
            try:
                object.__setattr__(self, "status", TransferStatus(self.status))
            except (TypeError, ValueError) as exc:
                raise ValueError("status must be a valid TransferStatus") from exc
        if self.status is TransferStatus.ADOPTED and self.adopted_at is None:
            raise ValueError("adopted transfer record requires adopted_at")

    def can_transition_to(self, new_status: TransferStatus) -> bool:
        if not isinstance(new_status, TransferStatus):
            raise TypeError("new_status must be a TransferStatus")
        return new_status in _ALLOWED_TRANSITIONS[self.status]

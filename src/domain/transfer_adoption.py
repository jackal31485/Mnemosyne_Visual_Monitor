"""Phase 14E controlled adoption of authorized cross-profile knowledge.

This module performs an explicit, deterministic adoption operation.

Adoption:
- requires a valid candidate, applicability analysis, and active authorization;
- creates a destination-owned learned representation;
- preserves the complete source-to-destination provenance chain;
- never copies raw source-memory content;
- never mutates source or destination inputs;
- never performs conflict resolution or revocation propagation.

Persistence and external synchronization are intentionally outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from .mental_model import MentalModel, MentalModelStatus
from .transfer_applicability import (
    ApplicabilityDecision,
    TransferApplicabilityAnalysis,
)
from .transfer_authorization import (
    AuthorizationMechanism,
    authorization_is_active,
)
from .transfer_contract import (
    TransferAuthorization,
    TransferCandidate,
    TransferRecord,
    TransferStatus,
)


class TransferAdoptionError(ValueError):
    """Raised when a controlled adoption cannot be performed."""


@dataclass(frozen=True, slots=True)
class DestinationLearnedRepresentation:
    """Destination-owned representation created by explicit transfer adoption.

    The embedded mental model remains the governed derived knowledge object.
    This wrapper adds the Phase 14 transfer lineage and authorization metadata
    needed to explain how the destination learned it.
    """

    learned_id: str
    destination_profile: str
    source_profile: str
    source_knowledge_id: str
    transfer_id: str
    candidate_id: str
    authorization_id: str
    source_memory_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    temporal_scope: tuple[str, ...]
    derivation_method: str
    authorization_actor: str
    authorization_mechanism: AuthorizationMechanism
    authorization_scope: str
    authorized_at: datetime
    authorization_expires_at: datetime | None
    adopted_at: datetime
    version: int
    status: TransferStatus
    mental_model: MentalModel

    def __post_init__(self) -> None:
        text_fields = (
            "learned_id",
            "destination_profile",
            "source_profile",
            "source_knowledge_id",
            "transfer_id",
            "candidate_id",
            "authorization_id",
            "derivation_method",
            "authorization_actor",
            "authorization_scope",
        )

        for name in text_fields:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())

        if self.source_profile == self.destination_profile:
            raise ValueError("source_profile and destination_profile must differ")

        for name in (
            "source_memory_ids",
            "observation_ids",
            "evidence_ids",
            "temporal_scope",
        ):
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

        if not self.evidence_ids:
            raise ValueError("evidence_ids must contain at least one identifier")

        if not isinstance(self.authorization_mechanism, AuthorizationMechanism):
            raise TypeError(
                "authorization_mechanism must be an AuthorizationMechanism"
            )

        for name in ("authorized_at", "adopted_at"):
            if not isinstance(getattr(self, name), datetime):
                raise TypeError(f"{name} must be a datetime")

        if self.authorization_expires_at is not None:
            if not isinstance(self.authorization_expires_at, datetime):
                raise TypeError(
                    "authorization_expires_at must be a datetime or None"
                )
            if self.authorization_expires_at < self.authorized_at:
                raise ValueError(
                    "authorization_expires_at must not precede authorized_at"
                )

        if self.adopted_at < self.authorized_at:
            raise ValueError("adopted_at must not precede authorized_at")

        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise TypeError("version must be an int")
        if self.version < 1:
            raise ValueError("version must be at least 1")

        if self.status is not TransferStatus.ADOPTED:
            raise ValueError(
                "destination learned representations must be ADOPTED"
            )

        if not isinstance(self.mental_model, MentalModel):
            raise TypeError("mental_model must be a MentalModel")

        if self.mental_model.source_profiles:
            if self.source_profile not in self.mental_model.source_profiles:
                raise ValueError(
                    "mental model source profiles must include source_profile"
                )

        if self.mental_model.temporal_scope != self.temporal_scope:
            raise ValueError(
                "mental model temporal scope must match adopted temporal scope"
            )


@dataclass(frozen=True, slots=True)
class TransferAdoptionResult:
    """Immutable result of one explicit controlled adoption."""

    previous_transfer_record: TransferRecord
    adopted_transfer_record: TransferRecord
    learned_representation: DestinationLearnedRepresentation


def _learned_id(
    *,
    transfer_id: str,
    destination_profile: str,
    source_knowledge_id: str,
) -> str:
    """Return a deterministic destination-learned identity."""

    material = "|".join(
        (
            transfer_id,
            destination_profile,
            source_knowledge_id,
        )
    )
    digest = sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"learned-{digest}"


def _validate_identity(
    candidate: TransferCandidate,
    analysis: TransferApplicabilityAnalysis,
    authorization: TransferAuthorization,
) -> None:
    """Validate that all Phase 14 governance identities agree."""

    if analysis.candidate_id != candidate.candidate_id:
        raise TransferAdoptionError(
            "analysis candidate ID does not match candidate"
        )

    if analysis.source_profile != candidate.source_profile:
        raise TransferAdoptionError(
            "analysis source profile does not match candidate"
        )

    if analysis.destination_profile != candidate.destination_profile:
        raise TransferAdoptionError(
            "analysis destination profile does not match candidate"
        )

    if analysis.source_knowledge_id != candidate.source_knowledge_id:
        raise TransferAdoptionError(
            "analysis knowledge ID does not match candidate"
        )

    if authorization.candidate_id != candidate.candidate_id:
        raise TransferAdoptionError(
            "authorization candidate ID does not match candidate"
        )

    if authorization.source_profile != candidate.source_profile:
        raise TransferAdoptionError(
            "authorization source profile does not match candidate"
        )

    if authorization.destination_profile != candidate.destination_profile:
        raise TransferAdoptionError(
            "authorization destination profile does not match candidate"
        )


def adopt_transfer(
    candidate: TransferCandidate,
    analysis: TransferApplicabilityAnalysis,
    authorization: TransferAuthorization,
    *,
    adopted_at: datetime,
    mental_model: MentalModel,
) -> TransferAdoptionResult:
    """Explicitly adopt authorized knowledge into the destination profile.

    This operation is pure: all supplied objects remain unchanged and no
    persistence or external synchronization occurs.
    """

    if not isinstance(candidate, TransferCandidate):
        raise TypeError("candidate must be a TransferCandidate")

    if not isinstance(analysis, TransferApplicabilityAnalysis):
        raise TypeError(
            "analysis must be a TransferApplicabilityAnalysis"
        )

    if not isinstance(authorization, TransferAuthorization):
        raise TypeError(
            "authorization must be a TransferAuthorization"
        )

    if not isinstance(adopted_at, datetime):
        raise TypeError("adopted_at must be a datetime")

    if not isinstance(mental_model, MentalModel):
        raise TypeError("mental_model must be a MentalModel")

    if candidate.status is not TransferStatus.CANDIDATE:
        raise TransferAdoptionError(
            "only CANDIDATE transfers may be adopted"
        )

    if analysis.decision is not ApplicabilityDecision.APPLICABLE:
        raise TransferAdoptionError(
            "only APPLICABLE transfers may be adopted"
        )

    _validate_identity(candidate, analysis, authorization)

    if not authorization_is_active(authorization, at=adopted_at):
        raise TransferAdoptionError(
            "transfer authorization is not active at adoption time"
        )

    if adopted_at < authorization.authorized_at:
        raise TransferAdoptionError(
            "adopted_at must not precede authorization"
        )

    if authorization.expires_at is not None and adopted_at > authorization.expires_at:
        raise TransferAdoptionError(
            "transfer authorization has expired"
        )

    if not candidate.supporting_evidence_ids:
        raise TransferAdoptionError(
            "transfer adoption requires supporting evidence"
        )

    if tuple(candidate.supporting_evidence_ids) != tuple(
        candidate.provenance.evidence_ids
    ):
        raise TransferAdoptionError(
            "candidate evidence provenance is incomplete"
        )

    if tuple(candidate.source_memory_ids) != tuple(
        candidate.provenance.source_memory_ids
    ):
        raise TransferAdoptionError(
            "candidate memory provenance is incomplete"
        )

    if tuple(candidate.observation_ids) != tuple(
        candidate.provenance.observation_ids
    ):
        raise TransferAdoptionError(
            "candidate observation provenance is incomplete"
        )

    if candidate.provenance.source_profile != candidate.source_profile:
        raise TransferAdoptionError(
            "candidate provenance source profile is invalid"
        )

    if candidate.provenance.destination_profile != candidate.destination_profile:
        raise TransferAdoptionError(
            "candidate provenance destination profile is invalid"
        )

    if candidate.provenance.source_knowledge_id != candidate.source_knowledge_id:
        raise TransferAdoptionError(
            "candidate provenance knowledge ID is invalid"
        )

    if mental_model.model_id != candidate.mental_model_id:
        raise TransferAdoptionError(
            "mental model ID does not match transfer candidate"
        )

    if mental_model.source_profiles:
        if candidate.source_profile not in mental_model.source_profiles:
            raise TransferAdoptionError(
                "mental model source provenance does not include source profile"
            )

    if mental_model.supporting_evidence_ids != candidate.supporting_evidence_ids:
        raise TransferAdoptionError(
            "mental model evidence must match transfer evidence"
        )

    if mental_model.supporting_observation_ids != candidate.observation_ids:
        raise TransferAdoptionError(
            "mental model observations must match transfer observations"
        )

    if mental_model.supporting_memory_ids != candidate.source_memory_ids:
        raise TransferAdoptionError(
            "mental model memories must match transfer memories"
        )

    if mental_model.temporal_scope != candidate.temporal_scope:
        raise TransferAdoptionError(
            "mental model temporal scope must match transfer temporal scope"
        )

    if mental_model.status not in {
        MentalModelStatus.VALIDATED,
        MentalModelStatus.ACTIVE,
    }:
        raise TransferAdoptionError(
            "adopted mental model must be VALIDATED or ACTIVE"
        )

    previous_record = TransferRecord(
        transfer_id=candidate.provenance.transfer_record_id,
        candidate_id=candidate.candidate_id,
        authorization_id=authorization.authorization_id,
        provenance=candidate.provenance,
        created_at=candidate.created_at or authorization.authorized_at,
        adopted_at=None,
        version=1,
        status=TransferStatus.AUTHORIZED,
    )

    adopted_record = TransferRecord(
        transfer_id=previous_record.transfer_id,
        candidate_id=previous_record.candidate_id,
        authorization_id=previous_record.authorization_id,
        provenance=previous_record.provenance,
        created_at=previous_record.created_at,
        adopted_at=adopted_at,
        version=previous_record.version,
        status=TransferStatus.ADOPTED,
    )

    learned = DestinationLearnedRepresentation(
        learned_id=_learned_id(
            transfer_id=previous_record.transfer_id,
            destination_profile=candidate.destination_profile,
            source_knowledge_id=candidate.source_knowledge_id,
        ),
        destination_profile=candidate.destination_profile,
        source_profile=candidate.source_profile,
        source_knowledge_id=candidate.source_knowledge_id,
        transfer_id=previous_record.transfer_id,
        candidate_id=candidate.candidate_id,
        authorization_id=authorization.authorization_id,
        source_memory_ids=candidate.source_memory_ids,
        observation_ids=candidate.observation_ids,
        evidence_ids=candidate.supporting_evidence_ids,
        temporal_scope=candidate.temporal_scope,
        derivation_method=(
            f"phase-14e-controlled-adoption:"
            f"{mental_model.derivation_method}"
        ),
        authorization_actor=authorization.actor,
        authorization_mechanism=authorization_mechanism(authorization),
        authorization_scope=authorization.scope,
        authorized_at=authorization.authorized_at,
        authorization_expires_at=authorization.expires_at,
        adopted_at=adopted_at,
        version=1,
        status=TransferStatus.ADOPTED,
        mental_model=mental_model,
    )

    return TransferAdoptionResult(
        previous_transfer_record=previous_record,
        adopted_transfer_record=adopted_record,
        learned_representation=learned,
    )


def authorization_mechanism(
    authorization: TransferAuthorization,
) -> AuthorizationMechanism:
    """Return the explicit authorization mechanism."""

    mechanism = authorization.mechanism

    try:
        return AuthorizationMechanism(mechanism)
    except (TypeError, ValueError) as exc:
        raise TransferAdoptionError(
            "authorization mechanism is required for controlled adoption"
        ) from exc



__all__ = [
    "DestinationLearnedRepresentation",
    "TransferAdoptionError",
    "TransferAdoptionResult",
    "adopt_transfer",
]

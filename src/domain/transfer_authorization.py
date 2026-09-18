"""Phase 14D explicit authorization for governed cross-profile transfer.

Authorization is a separate governance boundary from candidate generation,
applicability analysis, and destination adoption.

This module:
- requires an explicit authorization actor and mechanism;
- requires a valid Phase 14C applicability analysis;
- preserves candidate provenance;
- creates an authorized audit record;
- never adopts or mutates destination knowledge;
- never represents or copies raw private memory content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256

from .transfer_applicability import (
    ApplicabilityDecision,
    TransferApplicabilityAnalysis,
)
from .transfer_contract import (
    TransferAuthorization,
    TransferCandidate,
    TransferRecord,
    TransferStatus,
)


class AuthorizationMechanism(str, Enum):
    """Explicit mechanisms by which a transfer may be authorized."""

    HUMAN = "human"
    POLICY = "policy"
    REVIEW_APPROVAL = "review_approval"


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _required_datetime(name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    return value


def _authorization_id(
    candidate: TransferCandidate,
    actor: str,
    scope: str,
    authorized_at: datetime,
    mechanism: AuthorizationMechanism,
) -> str:
    material = "|".join(
        (
            candidate.candidate_id,
            candidate.source_profile,
            candidate.destination_profile,
            actor,
            scope,
            authorized_at.isoformat(),
            mechanism.value,
        )
    )
    digest = sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"auth-{digest}"


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """Explicit authorization request containing governance metadata only."""

    actor: str
    scope: str
    authorized_at: datetime
    mechanism: AuthorizationMechanism
    expires_at: datetime | None = None
    authorization_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor", _required_text("actor", self.actor))
        object.__setattr__(self, "scope", _required_text("scope", self.scope))
        object.__setattr__(
            self,
            "authorized_at",
            _required_datetime("authorized_at", self.authorized_at),
        )

        if not isinstance(self.mechanism, AuthorizationMechanism):
            try:
                object.__setattr__(
                    self,
                    "mechanism",
                    AuthorizationMechanism(self.mechanism),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "mechanism must be a valid AuthorizationMechanism"
                ) from exc

        if self.expires_at is not None:
            if not isinstance(self.expires_at, datetime):
                raise TypeError("expires_at must be a datetime or None")
            if self.expires_at < self.authorized_at:
                raise ValueError("expires_at must not precede authorized_at")

        if self.authorization_id is not None:
            object.__setattr__(
                self,
                "authorization_id",
                _required_text("authorization_id", self.authorization_id),
            )


def authorization_is_active(
    authorization: TransferAuthorization,
    *,
    at: datetime,
) -> bool:
    """Return whether authorization is usable at the supplied instant."""

    if not isinstance(authorization, TransferAuthorization):
        raise TypeError("authorization must be a TransferAuthorization")
    if not isinstance(at, datetime):
        raise TypeError("at must be a datetime")

    if authorization.revoked:
        return False

    if at < authorization.authorized_at:
        return False

    if authorization.expires_at is not None and at > authorization.expires_at:
        return False

    return True


def authorize_transfer(
    candidate: TransferCandidate,
    analysis: TransferApplicabilityAnalysis,
    request: AuthorizationRequest,
) -> tuple[TransferAuthorization, TransferRecord]:
    """Explicitly authorize a transfer without adopting it.

    Authorization is permitted only after Phase 14C analysis.  A normal
    applicable analysis requires an explicit authorization request.  A
    review-required analysis additionally requires the REVIEW_APPROVAL
    mechanism.

    The returned TransferRecord is AUTHORIZED only.  Destination adoption
    remains a separate Phase 14E operation.
    """

    if not isinstance(candidate, TransferCandidate):
        raise TypeError("candidate must be a TransferCandidate")

    if not isinstance(analysis, TransferApplicabilityAnalysis):
        raise TypeError(
            "analysis must be a TransferApplicabilityAnalysis"
        )

    if not isinstance(request, AuthorizationRequest):
        raise TypeError("request must be an AuthorizationRequest")

    if candidate.status is not TransferStatus.CANDIDATE:
        raise ValueError("only CANDIDATE transfers may be authorized")

    if analysis.candidate_id != candidate.candidate_id:
        raise ValueError("analysis candidate ID must match candidate")

    if analysis.source_profile != candidate.source_profile:
        raise ValueError("analysis source profile must match candidate")

    if analysis.destination_profile != candidate.destination_profile:
        raise ValueError("analysis destination profile must match candidate")

    if analysis.source_knowledge_id != candidate.source_knowledge_id:
        raise ValueError("analysis knowledge ID must match candidate")

    if analysis.decision is ApplicabilityDecision.NOT_APPLICABLE:
        raise ValueError("not-applicable transfers cannot be authorized")

    if (
        analysis.decision is ApplicabilityDecision.REVIEW_REQUIRED
        and request.mechanism is not AuthorizationMechanism.REVIEW_APPROVAL
    ):
        raise ValueError(
            "review-required transfers require explicit review approval"
        )

    authorization_id = request.authorization_id or _authorization_id(
        candidate,
        request.actor,
        request.scope,
        request.authorized_at,
        request.mechanism,
    )

    authorization = TransferAuthorization(
        authorization_id=authorization_id,
        candidate_id=candidate.candidate_id,
        source_profile=candidate.source_profile,
        destination_profile=candidate.destination_profile,
        actor=request.actor,
        authorized_at=request.authorized_at,
        scope=request.scope,
        mechanism=request.mechanism.value,
        expires_at=request.expires_at,
    )

    transfer_id = candidate.provenance.transfer_record_id

    record = TransferRecord(
        transfer_id=transfer_id,
        candidate_id=candidate.candidate_id,
        authorization_id=authorization.authorization_id,
        provenance=candidate.provenance,
        created_at=request.authorized_at,
        status=TransferStatus.AUTHORIZED,
    )

    return authorization, record

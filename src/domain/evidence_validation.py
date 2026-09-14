"""Phase 12D evidence validation and contradiction handling.

This module validates whether the evidence associated with a consolidation
candidate is currently eligible to support governed consolidation.

Validation is deliberately separate from persistence and consolidation.
It does not mutate evidence, observations, source memories, or candidates.

The validator preserves the distinction between:
- current support,
- historical traceability,
- contradiction,
- temporal incompatibility,
- incomplete provenance,
- unauthorized evidence, and
- unavailable source memory.

A successful validation result is an eligibility assessment only. It is not
authorization to consolidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


class EvidenceLifecycleState(str, Enum):
    """Lifecycle state relevant to current evidence support."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    PROMOTED = "promoted"
    REVOKED = "revoked"


class EvidenceValidationOutcome(str, Enum):
    """Governed result of validating consolidation evidence."""

    ELIGIBLE = "eligible"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """Immutable description of one evidence item used by a candidate.

    This is a validation input contract, not a replacement for the persisted
    evidence record. It carries only the governance facts required by 12D.
    """

    evidence_id: str
    source_profile: str
    source_memory_id: str | None
    lifecycle_state: EvidenceLifecycleState
    source_memory_exists: bool
    source_profile_authorized: bool
    provenance_complete: bool
    temporal_compatible: bool | None
    is_derived: bool = False

    def __post_init__(self) -> None:
        _required_text("evidence_id", self.evidence_id)
        _required_text("source_profile", self.source_profile)

        if self.source_memory_id is not None:
            _required_text("source_memory_id", self.source_memory_id)

        if not isinstance(self.lifecycle_state, EvidenceLifecycleState):
            try:
                object.__setattr__(
                    self,
                    "lifecycle_state",
                    EvidenceLifecycleState(self.lifecycle_state),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "lifecycle_state must be a valid EvidenceLifecycleState"
                ) from exc

        for name in (
            "source_memory_exists",
            "source_profile_authorized",
            "provenance_complete",
            "is_derived",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")

        if self.temporal_compatible is not None and not isinstance(
            self.temporal_compatible,
            bool,
        ):
            raise TypeError("temporal_compatible must be bool or None")


@dataclass(frozen=True, slots=True)
class EvidenceValidationPolicy:
    """Deterministic policy controlling evidence validation."""

    require_source_memory: bool = True
    require_authorized_profile: bool = True
    require_provenance: bool = True
    reject_derived_as_evidence: bool = True
    require_temporal_compatibility: bool = True
    reject_revoked_support: bool = True
    reject_non_promoted_support: bool = True
    require_contradiction_review: bool = True

    def __post_init__(self) -> None:
        for name in (
            "require_source_memory",
            "require_authorized_profile",
            "require_provenance",
            "reject_derived_as_evidence",
            "require_temporal_compatibility",
            "reject_revoked_support",
            "reject_non_promoted_support",
            "require_contradiction_review",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class EvidenceValidationResult:
    """Immutable explanation of a candidate's evidence validation."""

    candidate_id: str
    evidence: tuple[EvidenceReference, ...]
    valid_evidence_ids: tuple[str, ...]
    invalid_evidence_ids: tuple[str, ...]
    reasons: frozenset[str]
    contradictory_evidence_ids: tuple[str, ...]
    temporal_incompatibility: bool
    provenance_complete: bool
    all_support_current: bool
    outcome: EvidenceValidationOutcome
    proposed_consolidation_outcome: ConsolidationOutcome

    def __post_init__(self) -> None:
        _required_text("candidate_id", self.candidate_id)

        if not self.evidence:
            raise ValueError("evidence must contain at least one item")

        if any(not isinstance(item, EvidenceReference) for item in self.evidence):
            raise TypeError("evidence must contain EvidenceReference items")

        for name in (
            "valid_evidence_ids",
            "invalid_evidence_ids",
            "contradictory_evidence_ids",
        ):
            values = getattr(self, name)
            if any(
                not isinstance(value, str) or not value.strip()
                for value in values
            ):
                raise ValueError(f"{name} must contain non-empty text")
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicates")

        if not isinstance(self.reasons, frozenset):
            raise TypeError("reasons must be a frozenset")

        if any(
            not isinstance(reason, str) or not reason.strip()
            for reason in self.reasons
        ):
            raise ValueError("reasons must contain non-empty text")

        for name in (
            "temporal_incompatibility",
            "provenance_complete",
            "all_support_current",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")

        if not isinstance(self.outcome, EvidenceValidationOutcome):
            raise TypeError("outcome must be EvidenceValidationOutcome")

        if not isinstance(
            self.proposed_consolidation_outcome,
            ConsolidationOutcome,
        ):
            raise TypeError(
                "proposed_consolidation_outcome must be ConsolidationOutcome"
            )

    @property
    def is_eligible(self) -> bool:
        """Return whether current evidence passes all required checks."""
        return self.outcome is EvidenceValidationOutcome.ELIGIBLE

    @property
    def requires_review(self) -> bool:
        """Return whether evidence requires human/governed review."""
        return self.outcome in {
            EvidenceValidationOutcome.REVIEW_REQUIRED,
            EvidenceValidationOutcome.CONFLICT,
        }


class EvidenceValidator:
    """Validate evidence supporting a Phase 12 consolidation candidate."""

    def __init__(
        self,
        policy: EvidenceValidationPolicy | None = None,
    ) -> None:
        self.policy = policy or EvidenceValidationPolicy()

    def validate(
        self,
        candidate: ConsolidationCandidate,
        evidence: tuple[EvidenceReference, ...],
    ) -> EvidenceValidationResult:
        if not isinstance(candidate, ConsolidationCandidate):
            raise TypeError(
                "candidate must be a ConsolidationCandidate"
            )

        if not isinstance(evidence, tuple):
            raise TypeError("evidence must be a tuple")

        if not evidence:
            raise ValueError("evidence must contain at least one item")

        if any(not isinstance(item, EvidenceReference) for item in evidence):
            raise TypeError(
                "evidence must contain EvidenceReference items"
            )

        candidate_evidence_ids = set(candidate.supporting_evidence_ids)
        supplied_evidence_ids = {item.evidence_id for item in evidence}

        if candidate_evidence_ids - supplied_evidence_ids:
            missing = sorted(candidate_evidence_ids - supplied_evidence_ids)
            raise ValueError(
                "candidate supporting evidence is missing: "
                + ", ".join(missing)
            )

        reasons: set[str] = set()
        valid_ids: list[str] = []
        invalid_ids: list[str] = []
        contradictory_ids = tuple(
            sorted(candidate.contradictory_evidence_ids)
        )

        temporal_incompatibility = False
        provenance_complete = True
        all_support_current = True

        for item in evidence:
            invalid = False

            if (
                self.policy.require_source_memory
                and not item.source_memory_exists
            ):
                reasons.add("source_memory_missing")
                invalid = True

            if (
                self.policy.require_authorized_profile
                and not item.source_profile_authorized
            ):
                reasons.add("source_profile_unauthorized")
                invalid = True

            if (
                self.policy.require_provenance
                and not item.provenance_complete
            ):
                reasons.add("incomplete_provenance")
                provenance_complete = False
                invalid = True

            if (
                self.policy.reject_derived_as_evidence
                and item.is_derived
            ):
                reasons.add("derived_statement_not_evidence")
                invalid = True

            if (
                self.policy.reject_revoked_support
                and item.lifecycle_state
                is EvidenceLifecycleState.REVOKED
            ):
                reasons.add("evidence_revoked")
                all_support_current = False
                invalid = True

            if (
                self.policy.reject_non_promoted_support
                and item.lifecycle_state
                is not EvidenceLifecycleState.PROMOTED
            ):
                reasons.add("evidence_not_promoted")
                all_support_current = False
                invalid = True

            if item.temporal_compatible is False:
                reasons.add("temporal_incompatibility")
                temporal_incompatibility = True
                invalid = True
            elif (
                item.temporal_compatible is None
                and self.policy.require_temporal_compatibility
            ):
                reasons.add("temporal_compatibility_unknown")
                invalid = True

            if invalid:
                invalid_ids.append(item.evidence_id)
            else:
                valid_ids.append(item.evidence_id)

        if contradictory_ids:
            reasons.add("contradictory_evidence_present")

        if contradictory_ids and self.policy.require_contradiction_review:
            outcome = EvidenceValidationOutcome.CONFLICT
            proposed_outcome = ConsolidationOutcome.CONFLICT
        elif temporal_incompatibility:
            outcome = EvidenceValidationOutcome.REVIEW_REQUIRED
            proposed_outcome = ConsolidationOutcome.REVIEW_REQUIRED
        elif invalid_ids:
            outcome = EvidenceValidationOutcome.REJECTED
            proposed_outcome = ConsolidationOutcome.REVIEW_REQUIRED
        else:
            outcome = EvidenceValidationOutcome.ELIGIBLE
            proposed_outcome = ConsolidationOutcome.CANDIDATE

        return EvidenceValidationResult(
            candidate_id=candidate.candidate_id,
            evidence=tuple(evidence),
            valid_evidence_ids=tuple(sorted(valid_ids)),
            invalid_evidence_ids=tuple(sorted(invalid_ids)),
            reasons=frozenset(sorted(reasons)),
            contradictory_evidence_ids=contradictory_ids,
            temporal_incompatibility=temporal_incompatibility,
            provenance_complete=provenance_complete
            and all(item.provenance_complete for item in evidence),
            all_support_current=all_support_current,
            outcome=outcome,
            proposed_consolidation_outcome=proposed_outcome,
        )

"""Phase 14C applicability and benefit analysis contracts.

This module evaluates whether an already-generated transfer candidate appears
applicable and beneficial to its destination.

Analysis is deterministic, inspectable, and advisory.  It does not authorize,
adopt, persist, or mutate destination state.  Raw private memory content is
never represented.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _bounded_score(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a numeric score")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")
    return score


def _identifiers(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of identifiers, not text")
    materialized = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in materialized):
        raise ValueError(f"{name} must contain non-empty text")
    normalized = tuple(value.strip() for value in materialized)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    return tuple(sorted(normalized))


class ApplicabilityDecision(str, Enum):
    """Advisory Phase 14C applicability outcomes."""

    APPLICABLE = "applicable"
    REVIEW_REQUIRED = "review_required"
    NOT_APPLICABLE = "not_applicable"


class ContradictionSignal(str, Enum):
    """Destination contradiction state observed during analysis."""

    NONE = "none"
    POSSIBLE = "possible"
    STRONG = "strong"


@dataclass(frozen=True, slots=True)
class TransferApplicabilitySignals:
    """Inspectable normalized signals used by applicability analysis."""

    evidence_quality: float
    novelty: float
    entity_overlap: float
    relationship_overlap: float
    temporal_compatibility: float
    destination_knowledge_gap: float
    contradiction: ContradictionSignal = ContradictionSignal.NONE
    prior_transfer_redundancy: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "evidence_quality",
            "novelty",
            "entity_overlap",
            "relationship_overlap",
            "temporal_compatibility",
            "destination_knowledge_gap",
            "prior_transfer_redundancy",
        ):
            object.__setattr__(self, name, _bounded_score(name, getattr(self, name)))

        if not isinstance(self.contradiction, ContradictionSignal):
            try:
                object.__setattr__(
                    self,
                    "contradiction",
                    ContradictionSignal(self.contradiction),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "contradiction must be a valid ContradictionSignal"
                ) from exc


@dataclass(frozen=True, slots=True)
class TransferApplicabilityAnalysis:
    """Immutable, inspectable result of Phase 14C analysis.

    This record is advisory only.  It never constitutes authorization or
    adoption.
    """

    candidate_id: str
    source_profile: str
    destination_profile: str
    source_knowledge_id: str
    signals: TransferApplicabilitySignals
    benefit_score: float
    applicability_score: float
    decision: ApplicabilityDecision
    reasons: tuple[str, ...]
    derivation_method: str = "phase-14c-deterministic-applicability-analysis"

    def __post_init__(self) -> None:
        for name in (
            "candidate_id",
            "source_profile",
            "destination_profile",
            "source_knowledge_id",
            "derivation_method",
        ):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))

        if self.source_profile == self.destination_profile:
            raise ValueError("source_profile and destination_profile must differ")

        if not isinstance(self.signals, TransferApplicabilitySignals):
            raise TypeError("signals must be TransferApplicabilitySignals")

        object.__setattr__(
            self,
            "benefit_score",
            _bounded_score("benefit_score", self.benefit_score),
        )
        object.__setattr__(
            self,
            "applicability_score",
            _bounded_score("applicability_score", self.applicability_score),
        )

        if not isinstance(self.decision, ApplicabilityDecision):
            try:
                object.__setattr__(
                    self,
                    "decision",
                    ApplicabilityDecision(self.decision),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "decision must be a valid ApplicabilityDecision"
                ) from exc

        object.__setattr__(self, "reasons", _identifiers("reasons", self.reasons))
        if not self.reasons:
            raise ValueError("reasons must contain at least one explanation")


def analyze_transfer_applicability(
    candidate: object,
    signals: TransferApplicabilitySignals,
) -> TransferApplicabilityAnalysis:
    """Analyze an existing Phase 14 transfer candidate deterministically.

    The candidate is read only.  No authorization, adoption, persistence, or
    destination mutation occurs.
    """
    # Local import avoids making the analysis contract the owner of candidate
    # generation while still enforcing the Phase 14B boundary.
    from .transfer_contract import TransferCandidate

    if not isinstance(candidate, TransferCandidate):
        raise TypeError("candidate must be a TransferCandidate")
    if not isinstance(signals, TransferApplicabilitySignals):
        raise TypeError("signals must be TransferApplicabilitySignals")

    if candidate.status.value in {"rejected", "revoked"}:
        raise ValueError("rejected or revoked candidates cannot be analyzed")

    # Benefit emphasizes destination novelty/gap and source quality while
    # reducing the benefit of redundant prior transfers.
    benefit_score = (
        0.30 * signals.destination_knowledge_gap
        + 0.25 * signals.novelty
        + 0.20 * signals.evidence_quality
        + 0.10 * signals.entity_overlap
        + 0.05 * signals.relationship_overlap
        + 0.10 * signals.temporal_compatibility
    )
    benefit_score *= 1.0 - 0.5 * signals.prior_transfer_redundancy

    # Applicability is deliberately independent of benefit.  A useful fact
    # can still be inapplicable to a destination.
    applicability_score = (
        0.30 * signals.entity_overlap
        + 0.20 * signals.relationship_overlap
        + 0.25 * signals.temporal_compatibility
        + 0.15 * signals.destination_knowledge_gap
        + 0.10 * signals.evidence_quality
    )

    reasons: list[str] = []

    if signals.entity_overlap > 0:
        reasons.append("entity_overlap")
    if signals.relationship_overlap > 0:
        reasons.append("relationship_overlap")
    if signals.temporal_compatibility >= 0.5:
        reasons.append("temporal_compatibility")
    if signals.destination_knowledge_gap >= 0.5:
        reasons.append("destination_knowledge_gap")
    if signals.novelty >= 0.5:
        reasons.append("novel_information")
    if signals.evidence_quality >= 0.5:
        reasons.append("sufficient_evidence")

    if signals.contradiction is ContradictionSignal.STRONG:
        reasons.append("strong_destination_contradiction")
    elif signals.contradiction is ContradictionSignal.POSSIBLE:
        reasons.append("possible_destination_contradiction")

    if signals.prior_transfer_redundancy > 0:
        reasons.append("prior_transfer_redundancy")

    if not reasons:
        reasons.append("insufficient_applicability_signals")

    if signals.contradiction is ContradictionSignal.STRONG:
        decision = ApplicabilityDecision.REVIEW_REQUIRED
    elif (
        applicability_score >= 0.60
        and benefit_score >= 0.60
        and signals.temporal_compatibility > 0.0
        and signals.evidence_quality > 0.0
    ):
        decision = ApplicabilityDecision.APPLICABLE
    else:
        decision = ApplicabilityDecision.NOT_APPLICABLE

    return TransferApplicabilityAnalysis(
        candidate_id=candidate.candidate_id,
        source_profile=candidate.source_profile,
        destination_profile=candidate.destination_profile,
        source_knowledge_id=candidate.source_knowledge_id,
        signals=signals,
        benefit_score=benefit_score,
        applicability_score=applicability_score,
        decision=decision,
        reasons=tuple(reasons),
    )

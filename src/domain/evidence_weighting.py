"""Phase 12E deterministic evidence weighting.

Evidence weighting ranks evidence by explicit, explainable signals.

This module does not authorize consolidation and does not mutate candidates,
evidence, observations, source memories, or validation results.

The weighting contract deliberately distinguishes:

- evidence lifecycle eligibility;
- source-profile independence;
- source reliability when explicitly available;
- evidence confidence;
- evidence precision;
- temporal recency where explicitly available;
- corroboration;
- contradiction;
- provenance completeness.

No single composite score is authoritative.  The result is a deterministic
decision-support artifact for later governed consolidation stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .evidence_validation import (
    EvidenceReference,
    EvidenceValidationResult,
    EvidenceLifecycleState,
)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _score(name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")

    return value


def _count(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")

    if value < 0:
        raise ValueError(f"{name} cannot be negative")

    return value


class EvidenceWeightingStatus(str, Enum):
    """Status of an evidence item for weighting purposes."""

    CURRENT = "current"
    HISTORICAL = "historical"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class EvidenceWeightingPolicy:
    """Explicit deterministic weights for evidence-quality signals."""

    confidence_weight: float = 0.20
    precision_weight: float = 0.15
    reliability_weight: float = 0.15
    recency_weight: float = 0.10
    corroboration_weight: float = 0.15
    independence_weight: float = 0.10
    provenance_weight: float = 0.15

    def __post_init__(self) -> None:
        weights = (
            self.confidence_weight,
            self.precision_weight,
            self.reliability_weight,
            self.recency_weight,
            self.corroboration_weight,
            self.independence_weight,
            self.provenance_weight,
        )

        for value in weights:
            if not isinstance(value, (int, float)):
                raise TypeError("weight values must be numeric")
            if value < 0.0:
                raise ValueError("weight values cannot be negative")

        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("evidence weighting weights must sum to 1.0")


@dataclass(frozen=True, slots=True)
class EvidenceWeightReference:
    """Immutable quality signals associated with one evidence reference.

    Optional signals are represented explicitly rather than inferred.  A
    missing optional signal is treated as neutral for the composite score,
    while the result records that it was unavailable.
    """

    evidence: EvidenceReference
    confidence: float
    precision: float
    corroboration_count: int
    independent_source_count: int
    source_reliability: float | None = None
    temporal_recency: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceReference):
            raise TypeError("evidence must be an EvidenceReference")

        object.__setattr__(
            self,
            "confidence",
            _score("confidence", self.confidence),
        )
        object.__setattr__(
            self,
            "precision",
            _score("precision", self.precision),
        )
        object.__setattr__(
            self,
            "corroboration_count",
            _count("corroboration_count", self.corroboration_count),
        )
        object.__setattr__(
            self,
            "independent_source_count",
            _count(
                "independent_source_count",
                self.independent_source_count,
            ),
        )

        if self.source_reliability is not None:
            object.__setattr__(
                self,
                "source_reliability",
                _score(
                    "source_reliability",
                    self.source_reliability,
                ),
            )

        if self.temporal_recency is not None:
            object.__setattr__(
                self,
                "temporal_recency",
                _score(
                    "temporal_recency",
                    self.temporal_recency,
                ),
            )

    @property
    def evidence_id(self) -> str:
        """Return the underlying evidence identifier."""

        return self.evidence.evidence_id

    @property
    def source_profile(self) -> str:
        """Return the evidence source profile."""

        return self.evidence.source_profile


@dataclass(frozen=True, slots=True)
class EvidenceWeightResult:
    """Immutable deterministic weighting result for one evidence item."""

    evidence_id: str
    source_profile: str
    status: EvidenceWeightingStatus
    confidence: float
    precision: float
    reliability: float
    recency: float
    corroboration: float
    independence: float
    provenance: float
    composite_weight: float
    unavailable_signals: frozenset[str]
    reasons: frozenset[str]

    def __post_init__(self) -> None:
        _required_text("evidence_id", self.evidence_id)
        _required_text("source_profile", self.source_profile)

        if not isinstance(self.status, EvidenceWeightingStatus):
            raise TypeError("status must be EvidenceWeightingStatus")

        for name in (
            "confidence",
            "precision",
            "reliability",
            "recency",
            "corroboration",
            "independence",
            "provenance",
            "composite_weight",
        ):
            object.__setattr__(
                self,
                name,
                _score(name, getattr(self, name)),
            )

        if not isinstance(self.unavailable_signals, frozenset):
            raise TypeError("unavailable_signals must be a frozenset")

        if not isinstance(self.reasons, frozenset):
            raise TypeError("reasons must be a frozenset")

        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.unavailable_signals
        ):
            raise ValueError("unavailable_signals cannot contain empty values")

        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.reasons
        ):
            raise ValueError("reasons cannot contain empty values")


@dataclass(frozen=True, slots=True)
class EvidenceWeightingResult:
    """Immutable ranked weighting assessment for a validated evidence set."""

    candidate_id: str
    evidence: tuple[EvidenceWeightResult, ...]
    ranked_evidence_ids: tuple[str, ...]
    total_current_weight: float
    current_support_count: int
    independent_profile_count: int
    contradiction_present: bool
    recalculation_required: bool

    def __post_init__(self) -> None:
        _required_text("candidate_id", self.candidate_id)

        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise ValueError("evidence must be a non-empty tuple")

        if any(
            not isinstance(item, EvidenceWeightResult)
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain EvidenceWeightResult values"
            )

        ids = tuple(item.evidence_id for item in self.evidence)

        if len(ids) != len(set(ids)):
            raise ValueError("evidence cannot contain duplicate evidence IDs")

        if not isinstance(self.ranked_evidence_ids, tuple):
            raise TypeError("ranked_evidence_ids must be a tuple")

        if set(self.ranked_evidence_ids) != set(ids):
            raise ValueError(
                "ranked_evidence_ids must contain exactly all evidence IDs"
            )

        object.__setattr__(
            self,
            "total_current_weight",
            _score("total_current_weight", self.total_current_weight),
        )

        object.__setattr__(
            self,
            "current_support_count",
            _count(
                "current_support_count",
                self.current_support_count,
            ),
        )
        object.__setattr__(
            self,
            "independent_profile_count",
            _count(
                "independent_profile_count",
                self.independent_profile_count,
            ),
        )

        if not isinstance(self.contradiction_present, bool):
            raise TypeError("contradiction_present must be bool")

        if not isinstance(self.recalculation_required, bool):
            raise TypeError("recalculation_required must be bool")

    @property
    def current_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence currently eligible to support the candidate."""

        return tuple(
            item.evidence_id
            for item in self.evidence
            if item.status is EvidenceWeightingStatus.CURRENT
        )


class EvidenceWeigher:
    """Calculate deterministic evidence weights."""

    def __init__(
        self,
        policy: EvidenceWeightingPolicy | None = None,
    ) -> None:
        self.policy = policy or EvidenceWeightingPolicy()

    @staticmethod
    def _corroboration_score(count: int) -> float:
        """Map corroboration count deterministically into [0, 1]."""

        return min(float(count) / 3.0, 1.0)

    @staticmethod
    def _independence_score(count: int) -> float:
        """Map independent source count deterministically into [0, 1]."""

        return min(float(count) / 3.0, 1.0)

    def _weight(
        self,
        reference: EvidenceWeightReference,
        validation: EvidenceValidationResult,
    ) -> EvidenceWeightResult:
        evidence = reference.evidence
        evidence_id = evidence.evidence_id

        if evidence_id in validation.invalid_evidence_ids:
            if evidence.lifecycle_state is EvidenceLifecycleState.REVOKED:
                status = EvidenceWeightingStatus.HISTORICAL
                reasons = {"revoked_historical_trace"}
            else:
                status = EvidenceWeightingStatus.INELIGIBLE
                reasons = {"validation_ineligible"}
        else:
            status = EvidenceWeightingStatus.CURRENT
            reasons = {"current_support"}

        unavailable: set[str] = set()

        reliability = reference.source_reliability
        if reliability is None:
            reliability = 0.0
            unavailable.add("source_reliability")
            reasons.add("source_reliability_unavailable")

        recency = reference.temporal_recency
        if recency is None:
            recency = 0.0
            unavailable.add("temporal_recency")
            reasons.add("temporal_recency_unavailable")

        corroboration = self._corroboration_score(
            reference.corroboration_count,
        )
        independence = self._independence_score(
            reference.independent_source_count,
        )
        provenance = (
            1.0
            if evidence.provenance_complete
            else 0.0
        )

        if not evidence.provenance_complete:
            reasons.add("incomplete_provenance")

        if evidence.lifecycle_state is EvidenceLifecycleState.REVOKED:
            reasons.add("evidence_revoked")

        if status is not EvidenceWeightingStatus.CURRENT:
            composite = 0.0
        else:
            composite = (
                reference.confidence * self.policy.confidence_weight
                + reference.precision * self.policy.precision_weight
                + reliability * self.policy.reliability_weight
                + recency * self.policy.recency_weight
                + corroboration * self.policy.corroboration_weight
                + independence * self.policy.independence_weight
                + provenance * self.policy.provenance_weight
            )

        return EvidenceWeightResult(
            evidence_id=evidence_id,
            source_profile=evidence.source_profile,
            status=status,
            confidence=reference.confidence,
            precision=reference.precision,
            reliability=reliability,
            recency=recency,
            corroboration=corroboration,
            independence=independence,
            provenance=provenance,
            composite_weight=round(composite, 12),
            unavailable_signals=frozenset(sorted(unavailable)),
            reasons=frozenset(sorted(reasons)),
        )

    def weight(
        self,
        *,
        validation: EvidenceValidationResult,
        evidence: tuple[EvidenceWeightReference, ...],
    ) -> EvidenceWeightingResult:
        """Weight an evidence set against an existing validation result."""

        if not isinstance(validation, EvidenceValidationResult):
            raise TypeError(
                "validation must be an EvidenceValidationResult"
            )

        if not isinstance(evidence, tuple):
            raise TypeError("evidence must be a tuple")

        if not evidence:
            raise ValueError("evidence must contain at least one item")

        if any(
            not isinstance(item, EvidenceWeightReference)
            for item in evidence
        ):
            raise TypeError(
                "evidence must contain EvidenceWeightReference values"
            )

        evidence_ids = {item.evidence_id for item in evidence}

        if evidence_ids != {
            item.evidence_id for item in validation.evidence
        }:
            raise ValueError(
                "weighting evidence must exactly match validated evidence"
            )

        results = tuple(
            self._weight(item, validation)
            for item in evidence
        )

        ranked = tuple(
            item.evidence_id
            for item in sorted(
                results,
                key=lambda item: (
                    -item.composite_weight,
                    item.evidence_id,
                ),
            )
        )

        current = tuple(
            item
            for item in results
            if item.status is EvidenceWeightingStatus.CURRENT
        )

        profiles = {
            item.source_profile
            for item in current
        }

        recalculation_required = any(
            item.evidence.lifecycle_state
            is EvidenceLifecycleState.REVOKED
            for item in evidence
        )

        return EvidenceWeightingResult(
            candidate_id=validation.candidate_id,
            evidence=results,
            ranked_evidence_ids=ranked,
            total_current_weight=round(
                min(sum(item.composite_weight for item in current), 1.0),
                12,
            ),
            current_support_count=len(current),
            independent_profile_count=len(profiles),
            contradiction_present=bool(
                validation.contradictory_evidence_ids
            ),
            recalculation_required=recalculation_required,
        )

"""Phase 13C deterministic governance validation for mental models.

Validation consumes governed metadata and evidence evaluations.  It never
mutates source records, invents evidence, or activates a model.  A successful
validation returns a new immutable mental-model version in ``VALIDATED`` state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from .mental_model import MentalModel, MentalModelStatus


def _ids(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of identifiers")
    result = tuple(sorted({v.strip() for v in values if isinstance(v, str) and v.strip()}))
    if len(result) != len(tuple(values)) if not isinstance(values, (str, bytes)) else False:
        # This branch is intentionally not used for malformed values; validation
        # below gives the caller a deterministic reason.
        pass
    return result


@dataclass(frozen=True, slots=True)
class ValidationEvidence:
    """Governed evaluation of one supporting evidence record."""

    evidence_id: str
    promoted: bool = True
    revoked: bool = False
    source_memory_id: str = ""
    source_profile: str = ""
    quality: float = 1.0
    independent_group: str = ""
    contradictory: bool = False
    temporally_compatible: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("evidence_id must be non-empty text")
        if not isinstance(self.quality, (int, float)) or isinstance(self.quality, bool):
            raise TypeError("quality must be numeric")
        if not 0.0 <= float(self.quality) <= 1.0:
            raise ValueError("quality must be between 0.0 and 1.0")
        if self.revoked and self.promoted:
            # Promotion state may be historical in the source system, but a
            # revoked record cannot be current support.
            return
        for name in ("source_memory_id", "source_profile"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be text")


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """Explicit, testable governance thresholds for validation."""

    minimum_evidence: int = 2
    minimum_independent_groups: int = 2
    minimum_quality: float = 0.70
    require_temporal_compatibility: bool = True
    allow_cross_profile: bool = False

    def __post_init__(self) -> None:
        if self.minimum_evidence < 1:
            raise ValueError("minimum_evidence must be at least 1")
        if self.minimum_independent_groups < 1:
            raise ValueError("minimum_independent_groups must be at least 1")
        if not 0.0 <= self.minimum_quality <= 1.0:
            raise ValueError("minimum_quality must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class MentalModelValidationResult:
    """Explainable result; failed validation never changes the model."""

    model: MentalModel
    valid: bool
    reasons: tuple[str, ...]
    accepted_evidence_ids: tuple[str, ...]
    rejected_evidence_ids: tuple[str, ...]

    @property
    def validated_model(self) -> MentalModel | None:
        return self.model if self.valid else None


class MentalModelValidator:
    """Validate candidates using only explicit governed evidence metadata."""

    _METHOD = "phase-13c-governed-validation"

    def __init__(self, policy: ValidationPolicy | None = None) -> None:
        self.policy = policy or ValidationPolicy()

    def validate(
        self,
        model: MentalModel,
        evidence: Iterable[ValidationEvidence],
        *,
        policy: ValidationPolicy | None = None,
        authorized_profiles: Iterable[str] | None = None,
        current_memory_ids: Iterable[str] | None = None,
        validated_at: datetime | None = None,
    ) -> MentalModelValidationResult:
        if not isinstance(model, MentalModel):
            raise TypeError("model must be a MentalModel")
        if model.status is not MentalModelStatus.CANDIDATE:
            raise ValueError("only CANDIDATE mental models may be validated")

        active_policy = policy or self.policy
        records = tuple(evidence)
        by_id: dict[str, ValidationEvidence] = {}
        duplicate = False
        for item in records:
            if not isinstance(item, ValidationEvidence):
                raise TypeError("evidence must contain ValidationEvidence records")
            if item.evidence_id in by_id:
                duplicate = True
            by_id[item.evidence_id] = item

        reasons: list[str] = []
        if duplicate:
            reasons.append("duplicate_evidence_ids")

        expected = set(model.supporting_evidence_ids)
        supplied = set(by_id)
        missing = expected - supplied
        if missing:
            reasons.append("missing_supporting_evidence")

        authorized = set(authorized_profiles if authorized_profiles is not None else model.source_profiles)
        model_profiles = set(model.source_profiles)
        current_memories = (
            set(current_memory_ids)
            if current_memory_ids is not None
            else set(model.supporting_memory_ids)
        )

        accepted: list[str] = []
        rejected: list[str] = []
        for evidence_id in sorted(expected & supplied):
            item = by_id[evidence_id]
            reject_reason = None
            if item.revoked:
                reject_reason = "revoked_evidence"
            elif not item.promoted:
                reject_reason = "unpromoted_evidence"
            elif item.source_memory_id not in current_memories:
                reject_reason = "missing_or_unauthorized_source_memory"
            elif item.source_profile not in authorized or item.source_profile not in model_profiles:
                reject_reason = "unauthorized_profile"
            elif float(item.quality) < active_policy.minimum_quality:
                reject_reason = "insufficient_evidence_quality"
            elif item.contradictory:
                reject_reason = "contradictory_evidence"
            elif active_policy.require_temporal_compatibility and not item.temporally_compatible:
                reject_reason = "temporal_incompatibility"
            if reject_reason:
                rejected.append(evidence_id)
                reasons.append(f"{reject_reason}:{evidence_id}")
            else:
                accepted.append(evidence_id)

        if len(accepted) < active_policy.minimum_evidence:
            reasons.append("insufficient_current_support")

        groups = {by_id[e].independent_group or e for e in accepted}
        if len(groups) < active_policy.minimum_independent_groups:
            reasons.append("insufficient_independent_corroboration")

        profiles = {by_id[e].source_profile for e in accepted}
        if not active_policy.allow_cross_profile and len(profiles) > 1:
            reasons.append("cross_profile_validation_not_authorized")

        if set(model.contradictory_evidence_ids) & set(accepted):
            reasons.append("contradictory_support_marked_current")

        valid = not reasons
        timestamp = validated_at or model.updated_at
        if not isinstance(timestamp, datetime):
            raise TypeError("validated_at must be a datetime")

        if valid:
            validated_model = model.transition_to(MentalModelStatus.VALIDATED)
            validated_model = MentalModel(
                model_id=validated_model.model_id,
                model_type=validated_model.model_type,
                title=validated_model.title,
                description=validated_model.description,
                entity_ids=validated_model.entity_ids,
                relationship_ids=validated_model.relationship_ids,
                supporting_observation_ids=validated_model.supporting_observation_ids,
                supporting_evidence_ids=tuple(accepted),
                supporting_memory_ids=validated_model.supporting_memory_ids,
                source_profiles=validated_model.source_profiles,
                temporal_scope=validated_model.temporal_scope,
                confidence=validated_model.confidence,
                status=validated_model.status,
                version=validated_model.version,
                created_at=validated_model.created_at,
                updated_at=timestamp,
                provenance=validated_model.provenance,
                derivation_method=validated_model.derivation_method,
                contradictory_evidence_ids=tuple(sorted(set(validated_model.contradictory_evidence_ids) & set(accepted))),
                staleness_state="current",
            )
        else:
            validated_model = model

        return MentalModelValidationResult(
            model=validated_model,
            valid=valid,
            reasons=tuple(sorted(set(reasons))),
            accepted_evidence_ids=tuple(accepted),
            rejected_evidence_ids=tuple(rejected),
        )


__all__ = [
    "MentalModelValidationResult",
    "MentalModelValidator",
    "ValidationEvidence",
    "ValidationPolicy",
]

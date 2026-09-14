"""Phase 12C consolidation candidate modeling.

A consolidation candidate records why observations may represent the same
underlying knowledge while preserving observations, evidence, provenance,
temporal distinctions, and contradictory evidence.

A candidate is not a consolidation decision and never authorizes merging.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.domain.observation_similarity import (
    ObservationReference,
    ObservationSimilarityResult,
)


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} cannot be empty")
    return value.strip()


def _score(name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")

    return value


def _identifiers(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        values = tuple(values)

    normalized: list[str] = []

    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} cannot contain empty identifiers")
        normalized.append(value.strip())

    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} cannot contain duplicate identifiers")

    return tuple(normalized)


class ConsolidationOutcome(str, Enum):
    """Governed outcomes available to later consolidation stages."""

    KEEP_SEPARATE = "KEEP_SEPARATE"
    CANDIDATE = "CANDIDATE"
    CONSOLIDATE = "CONSOLIDATE"
    REFINE = "REFINE"
    CONFLICT = "CONFLICT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True)
class ConsolidationCandidate:
    """Immutable description of a proposed consolidation relationship."""

    candidate_id: str
    observations: tuple[ObservationReference, ...]
    similarity_result: ObservationSimilarityResult
    reasons: frozenset[str]
    entity_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    temporal_compatibility: float
    supporting_evidence_ids: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...]
    source_profiles: tuple[str, ...]
    confidence: float
    proposed_outcome: ConsolidationOutcome
    provenance_complete: bool

    def __post_init__(self) -> None:
        candidate_id = _required_text("candidate_id", self.candidate_id)
        object.__setattr__(self, "candidate_id", candidate_id)

        if not isinstance(self.observations, tuple):
            object.__setattr__(
                self,
                "observations",
                tuple(self.observations),
            )

        if len(self.observations) < 2:
            raise ValueError("observations must contain at least two references")

        for observation in self.observations:
            if not isinstance(observation, ObservationReference):
                raise TypeError(
                    "observations must contain ObservationReference values"
                )

        observation_ids = [item.observation_id for item in self.observations]

        if len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observations cannot contain duplicate observation IDs")

        if not isinstance(
            self.similarity_result,
            ObservationSimilarityResult,
        ):
            raise TypeError(
                "similarity_result must be an ObservationSimilarityResult"
            )

        if not isinstance(self.reasons, frozenset):
            object.__setattr__(
                self,
                "reasons",
                frozenset(self.reasons),
            )

        for reason in self.reasons:
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("reasons cannot contain empty values")

        object.__setattr__(
            self,
            "entity_ids",
            _identifiers("entity_ids", self.entity_ids),
        )
        object.__setattr__(
            self,
            "relationship_ids",
            _identifiers("relationship_ids", self.relationship_ids),
        )
        object.__setattr__(
            self,
            "supporting_evidence_ids",
            _identifiers(
                "supporting_evidence_ids",
                self.supporting_evidence_ids,
            ),
        )
        object.__setattr__(
            self,
            "contradictory_evidence_ids",
            _identifiers(
                "contradictory_evidence_ids",
                self.contradictory_evidence_ids,
            ),
        )
        object.__setattr__(
            self,
            "source_profiles",
            _identifiers("source_profiles", self.source_profiles),
        )

        object.__setattr__(
            self,
            "temporal_compatibility",
            _score(
                "temporal_compatibility",
                self.temporal_compatibility,
            ),
        )
        object.__setattr__(
            self,
            "confidence",
            _score("confidence", self.confidence),
        )

        if not isinstance(self.proposed_outcome, ConsolidationOutcome):
            try:
                object.__setattr__(
                    self,
                    "proposed_outcome",
                    ConsolidationOutcome(self.proposed_outcome),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "proposed_outcome must be a valid ConsolidationOutcome"
                ) from exc

        if not isinstance(self.provenance_complete, bool):
            raise TypeError("provenance_complete must be a bool")

        expected_profiles = tuple(
            sorted(
                {
                    observation.source_profile
                    for observation in self.observations
                }
            )
        )

        if self.source_profiles != expected_profiles:
            raise ValueError(
                "source_profiles must exactly match observation source profiles"
            )

        similarity_ids = {
            self.similarity_result.left.observation_id,
            self.similarity_result.right.observation_id,
        }

        if not similarity_ids.issubset(set(observation_ids)):
            raise ValueError(
                "similarity_result observations must be included in observations"
            )

    @property
    def is_candidate(self) -> bool:
        """Return whether this object represents a candidate outcome."""
        return self.proposed_outcome == ConsolidationOutcome.CANDIDATE

    @property
    def has_contradictory_evidence(self) -> bool:
        """Return whether contradictory evidence has been recorded."""
        return bool(self.contradictory_evidence_ids)

    @property
    def is_cross_profile(self) -> bool:
        """Return whether observations originate from multiple profiles."""
        return len(self.source_profiles) > 1

    @classmethod
    def from_similarity(
        cls,
        *,
        candidate_id: str,
        observations: tuple[ObservationReference, ...],
        similarity_result: ObservationSimilarityResult,
        reasons: frozenset[str] | set[str] | tuple[str, ...],
        entity_ids: tuple[str, ...] = (),
        relationship_ids: tuple[str, ...] = (),
        temporal_compatibility: float = 1.0,
        supporting_evidence_ids: tuple[str, ...] = (),
        contradictory_evidence_ids: tuple[str, ...] = (),
        confidence: float | None = None,
        provenance_complete: bool | None = None,
    ) -> "ConsolidationCandidate":
        """Create a candidate from an existing similarity result.

        This factory only creates a candidate record.  It does not authorize
        consolidation and does not perform evidence validation.
        """
        if not isinstance(
            similarity_result,
            ObservationSimilarityResult,
        ):
            raise TypeError(
                "similarity_result must be an ObservationSimilarityResult"
            )

        observation_tuple = tuple(observations)

        if confidence is None:
            confidence = similarity_result.similarity_score

        if provenance_complete is None:
            provenance_complete = all(
                observation.source_profile
                and observation.observation_id
                for observation in observation_tuple
            )

        profile_tuple = tuple(
            sorted(
                {
                    observation.source_profile
                    for observation in observation_tuple
                }
            )
        )

        return cls(
            candidate_id=candidate_id,
            observations=observation_tuple,
            similarity_result=similarity_result,
            reasons=frozenset(reasons),
            entity_ids=tuple(entity_ids),
            relationship_ids=tuple(relationship_ids),
            temporal_compatibility=temporal_compatibility,
            supporting_evidence_ids=tuple(supporting_evidence_ids),
            contradictory_evidence_ids=tuple(
                contradictory_evidence_ids
            ),
            source_profiles=profile_tuple,
            confidence=confidence,
            proposed_outcome=ConsolidationOutcome.CANDIDATE,
            provenance_complete=provenance_complete,
        )

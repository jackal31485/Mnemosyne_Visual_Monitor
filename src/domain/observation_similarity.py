"""Phase 12A observation similarity contracts.

Similarity is a signal for review or consolidation.

It is never authorization to merge observations.

This module deliberately contains no consolidation, mutation, promotion,
or synthesis behavior.  It provides deterministic value objects and
comparison logic for later governed Phase 12 stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


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


@dataclass(frozen=True)
class ObservationReference:
    """Stable reference to an existing observation.

    The reference contains metadata only.  It must never contain raw private
    memory content.
    """

    observation_id: str
    source_profile: str
    source_memory_id: str | None = None
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _required_text("observation_id", self.observation_id),
        )
        object.__setattr__(
            self,
            "source_profile",
            _required_text("source_profile", self.source_profile),
        )

        if self.source_memory_id is not None:
            object.__setattr__(
                self,
                "source_memory_id",
                _required_text("source_memory_id", self.source_memory_id),
            )

        if self.evidence_id is not None:
            object.__setattr__(
                self,
                "evidence_id",
                _required_text("evidence_id", self.evidence_id),
            )


@dataclass(frozen=True)
class ObservationSimilaritySignals:
    """Individual deterministic similarity signals.

    These signals describe similarity only.  They do not authorize
    consolidation.
    """

    normalized_text: float = 0.0
    semantic: float = 0.0
    shared_entities: float = 0.0
    shared_relationships: float = 0.0
    temporal_compatibility: float = 0.0
    shared_evidence: float = 0.0
    profile_overlap: float = 0.0
    explicit_identifier: float = 0.0
    observation_type: float = 0.0
    confidence: float = 0.0
    provenance: float = 0.0

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            object.__setattr__(self, name, _score(name, value))


@dataclass(frozen=True)
class ObservationSimilarityResult:
    """Deterministic result of comparing two observations.

    ``is_candidate`` means that the observations are sufficiently similar to
    be considered by a later governed consolidation stage.

    It explicitly does NOT mean that the observations may be merged.
    """

    left: ObservationReference
    right: ObservationReference
    signals: ObservationSimilaritySignals
    similarity_score: float
    is_candidate: bool
    reasons: FrozenSet[str]

    def __post_init__(self) -> None:
        if self.left.observation_id == self.right.observation_id:
            raise ValueError("cannot compare an observation with itself")

        object.__setattr__(
            self,
            "similarity_score",
            _score("similarity_score", self.similarity_score),
        )

        if not isinstance(self.is_candidate, bool):
            raise TypeError("is_candidate must be a bool")

        if not isinstance(self.reasons, frozenset):
            object.__setattr__(
                self,
                "reasons",
                frozenset(self.reasons),
            )


@dataclass(frozen=True)
class ObservationSimilarityPolicy:
    """Policy controlling deterministic candidate classification.

    The threshold determines whether an observation pair is worth considering
    as a candidate.  It does not authorize consolidation.
    """

    candidate_threshold: float = 0.80

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_threshold",
            _score("candidate_threshold", self.candidate_threshold),
        )


class ObservationSimilarity:
    """Compute deterministic observation similarity from supplied signals."""

    _WEIGHTS = {
        "normalized_text": 0.20,
        "semantic": 0.20,
        "shared_entities": 0.10,
        "shared_relationships": 0.10,
        "temporal_compatibility": 0.10,
        "shared_evidence": 0.05,
        "profile_overlap": 0.05,
        "explicit_identifier": 0.05,
        "observation_type": 0.05,
        "confidence": 0.05,
        "provenance": 0.05,
    }

    def __init__(
        self,
        policy: ObservationSimilarityPolicy | None = None,
    ) -> None:
        self.policy = policy or ObservationSimilarityPolicy()

    def compare(
        self,
        left: ObservationReference,
        right: ObservationReference,
        signals: ObservationSimilaritySignals,
    ) -> ObservationSimilarityResult:
        if not isinstance(left, ObservationReference):
            raise TypeError("left must be an ObservationReference")

        if not isinstance(right, ObservationReference):
            raise TypeError("right must be an ObservationReference")

        if not isinstance(signals, ObservationSimilaritySignals):
            raise TypeError(
                "signals must be an ObservationSimilaritySignals"
            )

        score = sum(
            getattr(signals, name) * weight
            for name, weight in self._WEIGHTS.items()
        )

        reasons: set[str] = set()

        if signals.normalized_text >= 0.80:
            reasons.add("normalized_text_similarity")

        if signals.semantic >= 0.80:
            reasons.add("semantic_similarity")

        if signals.shared_entities >= 0.80:
            reasons.add("shared_entities")

        if signals.shared_relationships >= 0.80:
            reasons.add("shared_relationships")

        if signals.temporal_compatibility >= 0.80:
            reasons.add("temporal_compatibility")

        if signals.explicit_identifier >= 0.80:
            reasons.add("explicit_identifier")

        if signals.provenance < 1.0:
            reasons.add("incomplete_provenance")

        return ObservationSimilarityResult(
            left=left,
            right=right,
            signals=signals,
            similarity_score=score,
            is_candidate=score >= self.policy.candidate_threshold,
            reasons=frozenset(reasons),
        )

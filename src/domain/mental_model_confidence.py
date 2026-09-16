"""Deterministic confidence estimation for validated mental models.

Phase 13D adds a descriptive confidence layer on top of the Phase 13C
validated mental-model contract.

Confidence is derived from governed evidence and must never be used as a
substitute for validation, promotion, or revocation decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0


class MentalModelConfidenceError(ValueError):
    """Raised when confidence inputs violate the 13D contract."""


@dataclass(frozen=True)
class MentalModelConfidence:
    """Deterministic confidence result for a mental model."""

    score: float
    supporting_evidence: int
    contradicting_evidence: int
    governed_evidence: int
    provenance_complete: bool

    @property
    def confidence(self) -> float:
        """Alias for the normalized confidence score."""
        return self.score

    def as_dict(self) -> dict[str, Any]:
        """Return a serialization-safe representation."""
        return {
            "score": self.score,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "governed_evidence": self.governed_evidence,
            "provenance_complete": self.provenance_complete,
        }


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _is_governed_evidence(evidence: Mapping[str, Any]) -> bool:
    """Return whether evidence is eligible to contribute to confidence.

    Evidence must be promoted and non-revoked.  When explicit governance
    fields are present they are authoritative; missing fields are rejected
    rather than silently treated as governed.
    """
    if "promoted" not in evidence:
        return False

    if evidence["promoted"] is not True:
        return False

    if "revoked" not in evidence:
        return False

    return evidence["revoked"] is not True


def _has_complete_provenance(evidence: Mapping[str, Any]) -> bool:
    """Return whether governed evidence has source provenance."""
    required = ("source_profile_id", "source_memory_id")
    return all(
        key in evidence
        and evidence[key] is not None
        and str(evidence[key]).strip() != ""
        for key in required
    )


def _evidence_polarity(evidence: Mapping[str, Any]) -> str:
    """Return normalized evidence polarity."""
    value = evidence.get("polarity")

    if not isinstance(value, str):
        raise MentalModelConfidenceError(
            "evidence polarity must be a string"
        )

    polarity = value.strip().lower()

    if polarity not in {"supporting", "contradicting"}:
        raise MentalModelConfidenceError(
            "evidence polarity must be 'supporting' or 'contradicting'"
        )

    return polarity


def _normalize_score(value: float) -> float:
    return round(
        max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, value)),
        6,
    )


def estimate_mental_model_confidence(
    evidence: Iterable[Mapping[str, Any]],
) -> MentalModelConfidence:
    """Estimate deterministic confidence from governed evidence.

    The calculation intentionally remains simple and explainable:

        supporting / (supporting + contradicting)

    No governed evidence produces a score of 0.0.

    Non-governed evidence does not contribute to the score.  However,
    malformed evidence objects are rejected so callers cannot accidentally
    obtain a plausible-looking confidence value from invalid input.

    This function is descriptive only.  It does not validate, promote,
    revoke, or mutate a mental model.
    """
    supporting = 0
    contradicting = 0
    governed = 0
    provenance_complete = True

    if evidence is None:
        raise MentalModelConfidenceError("evidence cannot be None")

    for item in evidence:
        if not _is_mapping(item):
            raise MentalModelConfidenceError(
                "each evidence item must be a mapping"
            )

        if not _is_governed_evidence(item):
            continue

        governed += 1
        provenance_complete = (
            provenance_complete and _has_complete_provenance(item)
        )

        polarity = _evidence_polarity(item)

        if polarity == "supporting":
            supporting += 1
        else:
            contradicting += 1

    total = supporting + contradicting

    if total == 0:
        score = 0.0
    else:
        score = supporting / total

    return MentalModelConfidence(
        score=_normalize_score(score),
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        governed_evidence=governed,
        provenance_complete=provenance_complete,
    )


def confidence_from_model(
    model: Mapping[str, Any],
) -> MentalModelConfidence:
    """Estimate confidence from a model containing an evidence collection."""
    if not _is_mapping(model):
        raise MentalModelConfidenceError("model must be a mapping")

    if "evidence" not in model:
        raise MentalModelConfidenceError(
            "model must contain an evidence collection"
        )

    evidence = model["evidence"]

    if isinstance(evidence, (str, bytes)) or not isinstance(
        evidence, Iterable
    ):
        raise MentalModelConfidenceError(
            "model evidence must be an iterable collection"
        )

    return estimate_mental_model_confidence(evidence)

"""Deterministic relationship classification primitives for Phase 10F.2.

This module classifies already-extracted relationship candidates without
persisting relationships, resolving entities, or modifying source memories.

The classifier deliberately keeps explicit and inferred relationships
distinct. It never promotes an inferred relationship to an explicit fact.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.services.relationship_extraction import (
    RELATIONSHIP_EXTRACTION_METHOD,
    RelationshipCandidate,
)


RELATIONSHIP_CLASSIFICATION_METHOD = "deterministic-v1"

VALID_RELATIONSHIP_KINDS = frozenset({"explicit", "inferred"})


@dataclass(frozen=True)
class ClassifiedRelationship:
    """A governed classification of a relationship candidate."""

    subject_mention: str
    predicate: str
    object_mention: str
    confidence: float
    relationship_kind: str
    extraction_method: str
    classification_method: str = RELATIONSHIP_CLASSIFICATION_METHOD


def classify_relationship(
    candidate: RelationshipCandidate,
) -> ClassifiedRelationship:
    """Classify one relationship candidate without changing its semantics.

    The candidate's relationship kind is authoritative. In particular,
    inferred relationships remain inferred and are never promoted to explicit.
    """
    if not isinstance(candidate, RelationshipCandidate):
        raise TypeError("candidate must be a RelationshipCandidate")

    if candidate.relationship_kind not in VALID_RELATIONSHIP_KINDS:
        raise ValueError(
            f"unsupported relationship kind: {candidate.relationship_kind}"
        )

    if not isinstance(candidate.confidence, (int, float)):
        raise TypeError("confidence must be numeric")

    confidence = float(candidate.confidence)

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")

    return ClassifiedRelationship(
        subject_mention=candidate.subject_mention,
        predicate=candidate.predicate,
        object_mention=candidate.object_mention,
        confidence=confidence,
        relationship_kind=candidate.relationship_kind,
        extraction_method=candidate.extraction_method
        or RELATIONSHIP_EXTRACTION_METHOD,
    )

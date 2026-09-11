from __future__ import annotations

import pytest

from src.services.relationship_classification import (
    RELATIONSHIP_CLASSIFICATION_METHOD,
    VALID_RELATIONSHIP_KINDS,
    ClassifiedRelationship,
    classify_relationship,
)
from src.services.relationship_extraction import RelationshipCandidate


def _candidate(
    *,
    subject: str = "Mnemosyne",
    predicate: str = "uses",
    object_: str = "FastAPI",
    confidence: float = 0.95,
    relationship_kind: str = "explicit",
    extraction_method: str = "deterministic-v1",
) -> RelationshipCandidate:
    return RelationshipCandidate(
        subject_mention=subject,
        predicate=predicate,
        object_mention=object_,
        confidence=confidence,
        relationship_kind=relationship_kind,
        extraction_method=extraction_method,
    )


def test_valid_relationship_kinds_are_explicit_and_inferred():
    assert VALID_RELATIONSHIP_KINDS == {"explicit", "inferred"}


def test_classifies_explicit_relationship():
    result = classify_relationship(_candidate())

    assert isinstance(result, ClassifiedRelationship)
    assert result.subject_mention == "Mnemosyne"
    assert result.predicate == "uses"
    assert result.object_mention == "FastAPI"
    assert result.confidence == 0.95
    assert result.relationship_kind == "explicit"
    assert result.extraction_method == "deterministic-v1"
    assert result.classification_method == RELATIONSHIP_CLASSIFICATION_METHOD


def test_inferred_relationship_remains_inferred():
    result = classify_relationship(
        _candidate(
            confidence=0.60,
            relationship_kind="inferred",
        )
    )

    assert result.relationship_kind == "inferred"
    assert result.confidence == 0.60


def test_classifier_does_not_promote_inferred_relationship():
    candidate = _candidate(
        confidence=0.99,
        relationship_kind="inferred",
    )

    result = classify_relationship(candidate)

    assert result.relationship_kind != "explicit"
    assert result.relationship_kind == candidate.relationship_kind


def test_classifier_preserves_relationship_identity():
    candidate = _candidate(
        subject="Hermes",
        predicate="uses",
        object_="agent-a:athena",
    )

    result = classify_relationship(candidate)

    assert result.subject_mention == "Hermes"
    assert result.predicate == "uses"
    assert result.object_mention == "agent-a:athena"


def test_classifier_preserves_custom_extraction_method():
    candidate = _candidate(extraction_method="future-extractor-v2")

    result = classify_relationship(candidate)

    assert result.extraction_method == "future-extractor-v2"


def test_classifier_normalizes_numeric_confidence_to_float():
    candidate = _candidate(confidence=1)

    result = classify_relationship(candidate)

    assert result.confidence == 1.0
    assert isinstance(result.confidence, float)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, 2.0])
def test_invalid_confidence_is_rejected(confidence):
    with pytest.raises(ValueError, match="between 0 and 1"):
        classify_relationship(_candidate(confidence=confidence))


def test_non_numeric_confidence_is_rejected():
    candidate = _candidate(confidence=0.5)
    object.__setattr__(candidate, "confidence", "high")

    with pytest.raises(TypeError, match="confidence must be numeric"):
        classify_relationship(candidate)


def test_invalid_relationship_kind_is_rejected():
    candidate = _candidate(relationship_kind="maybe")

    with pytest.raises(ValueError, match="unsupported relationship kind"):
        classify_relationship(candidate)


def test_invalid_candidate_type_is_rejected():
    with pytest.raises(TypeError, match="candidate must be a RelationshipCandidate"):
        classify_relationship(object())


def test_classifier_does_not_modify_candidate():
    candidate = _candidate()

    result = classify_relationship(candidate)

    assert candidate.relationship_kind == "explicit"
    assert candidate.confidence == 0.95
    assert result is not candidate


def test_classifier_does_not_expose_memory_content():
    result = classify_relationship(_candidate())

    assert not hasattr(result, "memory_content")
    assert not hasattr(result, "source_memory_content")
    assert not hasattr(result, "evidence_text")

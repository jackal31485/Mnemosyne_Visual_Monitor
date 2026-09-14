from __future__ import annotations

import pytest

from src.domain.consolidation_candidate import (
    ConsolidationCandidate,
    ConsolidationOutcome,
)
from src.domain.near_duplicate_detection import NearDuplicateDetector
from src.domain.observation_similarity import ObservationReference


def ref(observation_id: str, profile: str) -> ObservationReference:
    return ObservationReference(
        observation_id=observation_id,
        source_profile=profile,
        source_memory_id=f"memory-{observation_id}",
    )


def make_similarity():
    detector = NearDuplicateDetector()

    return detector.compare(
        left=ref("a", "Athena"),
        right=ref("b", "Horus"),
        left_text=(
            "SQLite is the authoritative Mnemosyne datastore."
        ),
        right_text=(
            "SQLite is the authoritative Mnemosyne datastore layer."
        ),
    )


def make_candidate(**overrides):
    similarity = overrides.pop("similarity", None) or make_similarity()

    values = {
        "candidate_id": "candidate-001",
        "observations": (
            ref("a", "Athena"),
            ref("b", "Horus"),
        ),
        "similarity_result": similarity.similarity_result,
        "reasons": frozenset(
            {
                "normalized_text_near_duplicate",
                "similarity_candidate_signal",
            }
        ),
        "entity_ids": ("entity-sqlite",),
        "relationship_ids": ("relationship-authoritative-store",),
        "temporal_compatibility": 1.0,
        "supporting_evidence_ids": ("evidence-a", "evidence-b"),
        "contradictory_evidence_ids": (),
        "source_profiles": ("Athena", "Horus"),
        "confidence": similarity.similarity_result.similarity_score,
        "proposed_outcome": ConsolidationOutcome.CANDIDATE,
        "provenance_complete": True,
    }
    values.update(overrides)

    return ConsolidationCandidate(**values)


def test_candidate_records_required_consolidation_context():
    candidate = make_candidate()

    assert candidate.candidate_id == "candidate-001"
    assert [item.observation_id for item in candidate.observations] == [
        "a",
        "b",
    ]
    assert candidate.entity_ids == ("entity-sqlite",)
    assert candidate.relationship_ids == (
        "relationship-authoritative-store",
    )
    assert candidate.supporting_evidence_ids == (
        "evidence-a",
        "evidence-b",
    )
    assert candidate.source_profiles == ("Athena", "Horus")
    assert candidate.is_candidate is True


def test_candidate_preserves_similarity_result():
    similarity = make_similarity()
    candidate = make_candidate(similarity=similarity)

    assert candidate.similarity_result is similarity.similarity_result
    assert (
        candidate.similarity_result.similarity_score
        == similarity.similarity_result.similarity_score
    )


def test_cross_profile_candidate_is_preserved():
    candidate = make_candidate()

    assert candidate.is_cross_profile is True
    assert candidate.source_profiles == ("Athena", "Horus")


def test_contradictory_evidence_is_preserved():
    candidate = make_candidate(
        contradictory_evidence_ids=("evidence-conflict",),
    )

    assert candidate.has_contradictory_evidence is True
    assert candidate.contradictory_evidence_ids == (
        "evidence-conflict",
    )


def test_candidate_never_becomes_authorized_by_model():
    candidate = make_candidate()

    assert candidate.is_candidate is True
    assert not hasattr(candidate, "consolidate")
    assert not hasattr(candidate, "authorized")


def test_candidate_is_immutable():
    candidate = make_candidate()

    with pytest.raises(AttributeError):
        candidate.confidence = 0.5


def test_at_least_two_observations_are_required():
    with pytest.raises(ValueError):
        make_candidate(
            observations=(ref("a", "Athena"),),
            source_profiles=("Athena",),
        )


def test_duplicate_observations_are_rejected():
    with pytest.raises(ValueError):
        make_candidate(
            observations=(
                ref("a", "Athena"),
                ref("a", "Horus"),
            ),
            source_profiles=("Athena", "Horus"),
        )


def test_source_profiles_must_match_observations():
    with pytest.raises(ValueError):
        make_candidate(
            source_profiles=("Athena",),
        )


def test_scores_are_bounded():
    with pytest.raises(ValueError):
        make_candidate(confidence=1.1)

    with pytest.raises(ValueError):
        make_candidate(temporal_compatibility=-0.1)


def test_proposed_outcome_is_explicit():
    candidate = make_candidate(
        proposed_outcome=ConsolidationOutcome.REVIEW_REQUIRED,
    )

    assert candidate.is_candidate is False
    assert (
        candidate.proposed_outcome
        == ConsolidationOutcome.REVIEW_REQUIRED
    )


def test_factory_creates_candidate_without_authorizing_consolidation():
    similarity = make_similarity()

    candidate = ConsolidationCandidate.from_similarity(
        candidate_id="candidate-002",
        observations=(
            ref("a", "Athena"),
            ref("b", "Horus"),
        ),
        similarity_result=similarity.similarity_result,
        reasons=similarity.reasons,
        entity_ids=("entity-sqlite",),
        relationship_ids=("relationship-authoritative-store",),
        supporting_evidence_ids=("evidence-a",),
        confidence=0.91,
    )

    assert candidate.is_candidate is True
    assert candidate.provenance_complete is True
    assert candidate.source_profiles == ("Athena", "Horus")
    assert not hasattr(candidate, "authorized")


def test_incomplete_provenance_can_be_recorded_but_not_hidden():
    candidate = make_candidate(
        provenance_complete=False,
    )

    assert candidate.provenance_complete is False

"""Phase 13B deterministic candidate-detection tests."""
from datetime import datetime, timezone

import pytest

from src.domain.mental_model import MentalModelStatus, MentalModelType
from src.domain.mental_model_candidates import (
    CandidateDetectionPolicy,
    CandidateObservation,
    CandidateRelationship,
    MentalModelCandidateDetector,
)

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def obs(i, *, key="sqlite", evidence=None, entities=("sqlite",), relationships=(), temporal=(), otype="fact", confidence=.9):
    return CandidateObservation(
        observation_id=f"obs-{i}", source_profile="jeeves", source_memory_id=f"mem-{i}",
        evidence_ids=tuple(evidence or (f"ev-{i}",)), entity_ids=entities,
        relationship_ids=relationships, temporal_scope=temporal, concept_key=key,
        observation_type=otype, confidence=confidence,
    )


def test_repeated_concept_generates_candidate():
    result = MentalModelCandidateDetector().detect([obs(1), obs(2)], generated_at=NOW)
    concepts = [item.model for item in result if item.model.model_type is MentalModelType.CONCEPT]
    assert len(concepts) == 1
    assert concepts[0].status is MentalModelStatus.CANDIDATE
    assert concepts[0].supporting_observation_ids == ("obs-1", "obs-2")
    assert concepts[0].supporting_evidence_ids == ("ev-1", "ev-2")


def test_single_observation_is_insufficient():
    assert MentalModelCandidateDetector().detect([obs(1)], generated_at=NOW) == ()


def test_same_observation_repeated_is_not_two_observations():
    item = obs(1)
    assert MentalModelCandidateDetector().detect([item, item], generated_at=NOW) == ()


def test_insufficient_distinct_evidence_is_rejected():
    assert MentalModelCandidateDetector().detect([obs(1, evidence=("ev-1",)), obs(2, evidence=("ev-1",))], generated_at=NOW) == ()


def test_unrelated_concepts_remain_separate():
    result = MentalModelCandidateDetector().detect([obs(1, key="sqlite"), obs(2, key="sqlite"), obs(3, key="python"), obs(4, key="python")], generated_at=NOW)
    concepts = [item.model for item in result if item.model.model_type is MentalModelType.CONCEPT]
    assert len(concepts) == 2
    assert {model.title for model in concepts} == {"Recurring concept: sqlite", "Recurring concept: python"}


def test_candidate_is_not_auto_validated_or_activated():
    result = MentalModelCandidateDetector().detect([obs(1), obs(2)], generated_at=NOW)
    assert all(item.model.status is MentalModelStatus.CANDIDATE for item in result)


def test_similarity_is_not_an_input_or_authorization_signal():
    a = obs(1)
    b = obs(2)
    result = MentalModelCandidateDetector().detect([a, b], generated_at=NOW)
    assert result
    assert "similarity" not in result[0].signal_reasons


def test_deterministic_model_id_and_order():
    detector = MentalModelCandidateDetector()
    left = detector.detect([obs(2), obs(1)], generated_at=NOW)
    right = detector.detect([obs(1), obs(2)], generated_at=NOW)
    assert [(x.model.model_id, x.model.supporting_observation_ids) for x in left] == [(x.model.model_id, x.model.supporting_observation_ids) for x in right]


def test_generated_at_is_reproducible():
    detector = MentalModelCandidateDetector()
    first = detector.detect([obs(1), obs(2)], generated_at=NOW)
    second = detector.detect([obs(1), obs(2)], generated_at=NOW)
    assert first == second


def test_provenance_matches_model_support():
    candidate = MentalModelCandidateDetector().detect([obs(1), obs(2)], generated_at=NOW)[0].model
    assert candidate.provenance.observation_ids == candidate.supporting_observation_ids
    assert candidate.provenance.evidence_ids == candidate.supporting_evidence_ids
    assert candidate.provenance.memory_ids == candidate.supporting_memory_ids
    assert candidate.provenance.source_profiles == candidate.source_profiles


def test_no_raw_memory_content_is_present():
    candidate = MentalModelCandidateDetector().detect([obs(1), obs(2)], generated_at=NOW)[0].model
    assert not hasattr(candidate, "memory_content")
    assert "mem-1" in candidate.supporting_memory_ids


def test_profile_provenance_is_preserved():
    items = [obs(1), obs(2)]
    result = MentalModelCandidateDetector().detect(items, generated_at=NOW)[0].model
    assert result.source_profiles == ("jeeves",)


def test_minimum_confidence_can_filter_candidates():
    detector = MentalModelCandidateDetector(CandidateDetectionPolicy(minimum_confidence=.95))
    assert detector.detect([obs(1, confidence=.9), obs(2, confidence=.9)], generated_at=NOW) == ()


def test_relationship_candidate_requires_repeated_relationships():
    relationships = [
        CandidateRelationship("rel-1", "jeeves", "mem-1", ("obs-1",), ("ev-1",), "a", "b", "uses"),
        CandidateRelationship("rel-2", "jeeves", "mem-2", ("obs-2",), ("ev-2",), "a", "b", "uses"),
    ]
    result = MentalModelCandidateDetector().detect([], relationships=relationships, generated_at=NOW)
    models = [item.model for item in result if item.model.model_type is MentalModelType.RELATIONSHIP]
    assert len(models) == 1
    assert models[0].relationship_ids == ("rel-1", "rel-2")
    assert models[0].supporting_observation_ids == ("obs-1", "obs-2")


def test_relationship_candidate_preserves_relationship_evidence():
    relationships = [
        CandidateRelationship("rel-1", "jeeves", "mem-1", ("obs-1",), ("ev-1",), "a", "b", "uses"),
        CandidateRelationship("rel-2", "jeeves", "mem-2", ("obs-2",), ("ev-2",), "a", "b", "uses"),
    ]
    model = MentalModelCandidateDetector().detect([], relationships=relationships, generated_at=NOW)[0].model
    assert model.supporting_evidence_ids == ("ev-1", "ev-2")


def test_temporal_candidate_requires_multiple_temporal_values():
    result = MentalModelCandidateDetector().detect([obs(1, temporal=("2025",)), obs(2, temporal=("2026",))], generated_at=NOW)
    assert any(item.model.model_type is MentalModelType.TEMPORAL for item in result)


def test_single_temporal_value_does_not_create_temporal_model():
    result = MentalModelCandidateDetector().detect([obs(1, temporal=("current",)), obs(2, temporal=("current",))], generated_at=NOW)
    assert not any(item.model.model_type is MentalModelType.TEMPORAL for item in result)


def test_expectation_candidate_is_explicitly_derived():
    result = MentalModelCandidateDetector().detect([obs(1, otype="expectation"), obs(2, otype="expectation")], generated_at=NOW)
    expectations = [item.model for item in result if item.model.model_type is MentalModelType.EXPECTATION]
    assert len(expectations) == 1
    assert "not a guarantee" in expectations[0].description


def test_expectation_requires_repetition():
    result = MentalModelCandidateDetector().detect([obs(1, otype="expectation")], generated_at=NOW)
    assert not any(item.model.model_type is MentalModelType.EXPECTATION for item in result)


def test_invalid_observation_type_is_rejected():
    with pytest.raises(TypeError):
        MentalModelCandidateDetector().detect([object()], generated_at=NOW)


def test_invalid_relationship_type_is_rejected():
    with pytest.raises(TypeError):
        MentalModelCandidateDetector().detect([], relationships=[object()], generated_at=NOW)


def test_relationship_requires_observation_lineage():
    with pytest.raises(ValueError):
        CandidateRelationship("rel-1", "jeeves", "mem-1", (), ("ev-1",), "a", "b", "uses")


def test_candidate_detection_does_not_mutate_inputs():
    items = [obs(1), obs(2)]
    before = tuple(items)
    MentalModelCandidateDetector().detect(items, generated_at=NOW)
    assert tuple(items) == before

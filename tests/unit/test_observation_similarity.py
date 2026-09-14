from __future__ import annotations

import pytest

from src.domain.observation_similarity import (
    ObservationReference,
    ObservationSimilarity,
    ObservationSimilarityPolicy,
    ObservationSimilaritySignals,
)


def reference(
    observation_id: str,
    profile: str = "Horus",
) -> ObservationReference:
    return ObservationReference(
        observation_id=observation_id,
        source_profile=profile,
        source_memory_id=f"memory-{observation_id}",
    )


def compatible_signals() -> ObservationSimilaritySignals:
    return ObservationSimilaritySignals(
        normalized_text=1.0,
        semantic=1.0,
        shared_entities=1.0,
        shared_relationships=1.0,
        temporal_compatibility=1.0,
        shared_evidence=1.0,
        profile_overlap=1.0,
        explicit_identifier=1.0,
        observation_type=1.0,
        confidence=1.0,
        provenance=1.0,
    )


def test_reference_requires_observation_id():
    with pytest.raises(ValueError):
        ObservationReference(
            observation_id="",
            source_profile="Horus",
        )


def test_reference_requires_source_profile():
    with pytest.raises(ValueError):
        ObservationReference(
            observation_id="obs-1",
            source_profile="",
        )


def test_signal_scores_must_be_between_zero_and_one():
    with pytest.raises(ValueError):
        ObservationSimilaritySignals(semantic=1.1)

    with pytest.raises(ValueError):
        ObservationSimilaritySignals(semantic=-0.1)


def test_policy_threshold_must_be_between_zero_and_one():
    with pytest.raises(ValueError):
        ObservationSimilarityPolicy(candidate_threshold=1.1)


def test_identical_observation_cannot_be_compared_with_itself():
    ref = reference("obs-1")

    with pytest.raises(ValueError):
        ObservationSimilarity().compare(
            ref,
            ref,
            compatible_signals(),
        )


def test_high_similarity_creates_candidate():
    result = ObservationSimilarity().compare(
        reference("obs-1"),
        reference("obs-2"),
        compatible_signals(),
    )

    assert result.is_candidate is True
    assert result.similarity_score == pytest.approx(1.0)
    assert "normalized_text_similarity" in result.reasons
    assert "semantic_similarity" in result.reasons


def test_low_similarity_does_not_create_candidate():
    signals = ObservationSimilaritySignals(
        normalized_text=0.2,
        semantic=0.2,
        shared_entities=0.0,
        shared_relationships=0.0,
        temporal_compatibility=0.0,
        shared_evidence=0.0,
        profile_overlap=0.0,
        explicit_identifier=0.0,
        observation_type=1.0,
        confidence=0.5,
        provenance=1.0,
    )

    result = ObservationSimilarity().compare(
        reference("obs-1"),
        reference("obs-2"),
        signals,
    )

    assert result.is_candidate is False
    assert result.similarity_score < 0.80


def test_similarity_is_deterministic():
    engine = ObservationSimilarity()
    signals = ObservationSimilaritySignals(
        normalized_text=0.9,
        semantic=0.8,
        shared_entities=0.7,
        shared_relationships=0.6,
        temporal_compatibility=1.0,
        shared_evidence=0.5,
        profile_overlap=0.5,
        explicit_identifier=0.0,
        observation_type=1.0,
        confidence=0.8,
        provenance=1.0,
    )

    first = engine.compare(
        reference("obs-a", "Horus"),
        reference("obs-b", "Odin"),
        signals,
    )

    second = engine.compare(
        reference("obs-a", "Horus"),
        reference("obs-b", "Odin"),
        signals,
    )

    assert first == second


def test_incomplete_provenance_is_visible_in_result():
    signals = compatible_signals()
    signals = ObservationSimilaritySignals(
        normalized_text=signals.normalized_text,
        semantic=signals.semantic,
        shared_entities=signals.shared_entities,
        shared_relationships=signals.shared_relationships,
        temporal_compatibility=signals.temporal_compatibility,
        shared_evidence=signals.shared_evidence,
        profile_overlap=signals.profile_overlap,
        explicit_identifier=signals.explicit_identifier,
        observation_type=signals.observation_type,
        confidence=signals.confidence,
        provenance=0.5,
    )

    result = ObservationSimilarity().compare(
        reference("obs-1"),
        reference("obs-2"),
        signals,
    )

    assert result.is_candidate is True
    assert "incomplete_provenance" in result.reasons


def test_similarity_result_does_not_authorize_consolidation():
    result = ObservationSimilarity().compare(
        reference("obs-1"),
        reference("obs-2"),
        compatible_signals(),
    )

    assert result.is_candidate is True
    assert not hasattr(result, "consolidate")
    assert not hasattr(result, "authorized")

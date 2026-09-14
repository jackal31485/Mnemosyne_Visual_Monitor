from __future__ import annotations

import pytest

from src.domain.near_duplicate_detection import (
    NearDuplicateDetector,
    NearDuplicatePolicy,
    normalize_observation_text,
    sequence_similarity,
    token_jaccard,
)
from src.domain.observation_similarity import ObservationReference


def ref(observation_id: str, profile: str = "Horus"):
    return ObservationReference(
        observation_id=observation_id,
        source_profile=profile,
        source_memory_id=f"memory-{observation_id}",
    )


def test_normalization_is_deterministic():
    assert (
        normalize_observation_text(
            "  SQLite,  is the AUTHORITATIVE Mnemosyne datastore. "
        )
        == "sqlite is the authoritative mnemosyne datastore"
    )


def test_normalization_does_not_change_original_text():
    original = "SQLite, is the authoritative Mnemosyne datastore."
    normalize_observation_text(original)
    assert original == "SQLite, is the authoritative Mnemosyne datastore."


def test_exact_normalized_text_is_detected():
    detector = NearDuplicateDetector()

    result = detector.compare(
        left=ref("a"),
        right=ref("b"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="  SQLite is the authoritative Mnemosyne datastore.  ",
    )

    assert result.is_exact_duplicate is True
    assert result.is_near_duplicate is False
    assert result.left_text_hash == result.right_text_hash
    assert "normalized_text_exact" in result.reasons


def test_near_duplicate_wording_is_detected():
    detector = NearDuplicateDetector()

    result = detector.compare(
        left=ref("a", "Athena"),
        right=ref("b", "Horus"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="SQLite is the authoritative Mnemosyne datastore layer.",
    )

    assert result.is_exact_duplicate is False
    assert result.is_near_duplicate is True
    assert result.normalized_text_similarity >= 0.88
    assert result.token_similarity >= 0.75
    assert "normalized_text_near_duplicate" in result.reasons


def test_semantically_related_but_lexically_different_text_is_not_textual_near_duplicate():
    detector = NearDuplicateDetector()

    result = detector.compare(
        left=ref("a", "Athena"),
        right=ref("b", "Horus"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="Mnemosyne uses SQLite as its authoritative storage layer.",
    )

    assert result.is_exact_duplicate is False
    assert result.is_near_duplicate is False
    assert result.normalized_text_similarity < 0.88
    assert result.token_similarity < 0.75


def test_unrelated_observations_remain_separate():
    detector = NearDuplicateDetector()

    result = detector.compare(
        left=ref("a"),
        right=ref("b"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="The temporal graph records historical state transitions.",
    )

    assert result.is_exact_duplicate is False
    assert result.is_near_duplicate is False
    assert result.normalized_text_similarity < 0.88


def test_token_jaccard_is_deterministic():
    first = token_jaccard(
        "SQLite is authoritative storage",
        "SQLite is the authoritative storage",
    )
    second = token_jaccard(
        "SQLite is authoritative storage",
        "SQLite is the authoritative storage",
    )

    assert first == second
    assert first > 0.75


def test_sequence_similarity_is_deterministic():
    first = sequence_similarity(
        "SQLite is authoritative storage",
        "SQLite is the authoritative storage",
    )
    second = sequence_similarity(
        "SQLite is authoritative storage",
        "SQLite is the authoritative storage",
    )

    assert first == second


def test_thresholds_are_validated():
    with pytest.raises(ValueError):
        NearDuplicatePolicy(
            near_duplicate_threshold=1.1,
        )

    with pytest.raises(ValueError):
        NearDuplicatePolicy(
            near_duplicate_threshold=0.95,
            exact_threshold=0.90,
        )


def test_supplied_similarity_signals_are_preserved_except_text_signal():
    from src.domain.observation_similarity import (
        ObservationSimilaritySignals,
    )

    detector = NearDuplicateDetector()

    signals = ObservationSimilaritySignals(
        normalized_text=0.0,
        semantic=0.9,
        shared_entities=0.8,
        shared_relationships=0.7,
        temporal_compatibility=1.0,
        shared_evidence=0.6,
        profile_overlap=0.5,
        explicit_identifier=0.0,
        observation_type=1.0,
        confidence=0.9,
        provenance=1.0,
    )

    result = detector.compare(
        left=ref("a"),
        right=ref("b"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="Mnemosyne uses SQLite as its authoritative storage layer.",
        signals=signals,
    )

    assert result.similarity_result.signals.semantic == 0.9
    assert result.similarity_result.signals.shared_entities == 0.8
    assert result.similarity_result.signals.provenance == 1.0


def test_profile_identity_is_preserved():
    detector = NearDuplicateDetector()

    result = detector.compare(
        left=ref("a", "Athena"),
        right=ref("b", "Horus"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="SQLite is the authoritative Mnemosyne datastore.",
    )

    assert result.left.source_profile == "Athena"
    assert result.right.source_profile == "Horus"


def test_detection_does_not_authorize_consolidation():
    detector = NearDuplicateDetector()

    result = detector.compare(
        left=ref("a"),
        right=ref("b"),
        left_text="SQLite is the authoritative Mnemosyne datastore.",
        right_text="SQLite is the authoritative Mnemosyne datastore.",
    )

    assert result.is_exact_duplicate is True
    assert not hasattr(result, "consolidate")
    assert not hasattr(result, "authorized")


def test_empty_observation_is_rejected():
    detector = NearDuplicateDetector()

    with pytest.raises(ValueError):
        detector.compare(
            left=ref("a"),
            right=ref("b"),
            left_text="",
            right_text="SQLite is authoritative.",
        )

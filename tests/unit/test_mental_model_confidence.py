"""Tests for Phase 13D mental-model confidence estimation."""

from __future__ import annotations

import pytest

from src.domain.mental_model_confidence import (
    MentalModelConfidenceError,
    confidence_from_model,
    estimate_mental_model_confidence,
)


def evidence(
    *,
    polarity: str = "supporting",
    promoted: bool = True,
    revoked: bool = False,
    source_profile_id: str = "profile-1",
    source_memory_id: str = "memory-1",
) -> dict[str, object]:
    return {
        "polarity": polarity,
        "promoted": promoted,
        "revoked": revoked,
        "source_profile_id": source_profile_id,
        "source_memory_id": source_memory_id,
    }


def test_all_supporting_evidence_produces_full_confidence() -> None:
    result = estimate_mental_model_confidence(
        [
            evidence(source_memory_id="memory-1"),
            evidence(source_memory_id="memory-2"),
        ]
    )

    assert result.score == 1.0
    assert result.confidence == 1.0
    assert result.supporting_evidence == 2
    assert result.contradicting_evidence == 0
    assert result.governed_evidence == 2
    assert result.provenance_complete is True


def test_all_contradicting_evidence_produces_zero_confidence() -> None:
    result = estimate_mental_model_confidence(
        [
            evidence(
                polarity="contradicting",
                source_memory_id="memory-1",
            ),
            evidence(
                polarity="contradicting",
                source_memory_id="memory-2",
            ),
        ]
    )

    assert result.score == 0.0
    assert result.supporting_evidence == 0
    assert result.contradicting_evidence == 2
    assert result.governed_evidence == 2


def test_balanced_evidence_produces_half_confidence() -> None:
    result = estimate_mental_model_confidence(
        [
            evidence(source_memory_id="memory-1"),
            evidence(
                polarity="contradicting",
                source_memory_id="memory-2",
            ),
        ]
    )

    assert result.score == 0.5
    assert result.supporting_evidence == 1
    assert result.contradicting_evidence == 1


def test_non_governed_evidence_does_not_contribute() -> None:
    result = estimate_mental_model_confidence(
        [
            evidence(source_memory_id="memory-1"),
            evidence(
                polarity="contradicting",
                promoted=False,
                source_memory_id="memory-2",
            ),
            evidence(
                polarity="contradicting",
                revoked=True,
                source_memory_id="memory-3",
            ),
        ]
    )

    assert result.score == 1.0
    assert result.supporting_evidence == 1
    assert result.contradicting_evidence == 0
    assert result.governed_evidence == 1


def test_no_governed_evidence_produces_zero_confidence() -> None:
    result = estimate_mental_model_confidence(
        [
            evidence(promoted=False),
            evidence(revoked=True),
        ]
    )

    assert result.score == 0.0
    assert result.supporting_evidence == 0
    assert result.contradicting_evidence == 0
    assert result.governed_evidence == 0


def test_missing_provenance_is_reported() -> None:
    item = evidence()
    del item["source_memory_id"]

    result = estimate_mental_model_confidence([item])

    assert result.score == 1.0
    assert result.provenance_complete is False
    assert result.governed_evidence == 1


def test_missing_provenance_does_not_change_evidence_score() -> None:
    complete = estimate_mental_model_confidence(
        [evidence(source_memory_id="memory-1")]
    )

    incomplete_item = evidence(source_memory_id="memory-1")
    del incomplete_item["source_profile_id"]

    incomplete = estimate_mental_model_confidence([incomplete_item])

    assert incomplete.score == complete.score
    assert incomplete.governed_evidence == complete.governed_evidence
    assert incomplete.provenance_complete is False


def test_confidence_is_deterministic() -> None:
    items = [
        evidence(source_memory_id="memory-1"),
        evidence(
            polarity="contradicting",
            source_memory_id="memory-2",
        ),
        evidence(source_memory_id="memory-3"),
    ]

    first = estimate_mental_model_confidence(items)
    second = estimate_mental_model_confidence(items)

    assert first == second


def test_result_serializes_to_expected_shape() -> None:
    result = estimate_mental_model_confidence(
        [evidence(source_memory_id="memory-1")]
    )

    assert result.as_dict() == {
        "score": 1.0,
        "supporting_evidence": 1,
        "contradicting_evidence": 0,
        "governed_evidence": 1,
        "provenance_complete": True,
    }


def test_model_wrapper_reads_evidence_collection() -> None:
    model = {
        "model_id": "model-1",
        "evidence": [
            evidence(source_memory_id="memory-1"),
            evidence(
                polarity="contradicting",
                source_memory_id="memory-2",
            ),
        ],
    }

    result = confidence_from_model(model)

    assert result.score == 0.5
    assert result.supporting_evidence == 1
    assert result.contradicting_evidence == 1


def test_none_evidence_is_rejected() -> None:
    with pytest.raises(MentalModelConfidenceError):
        estimate_mental_model_confidence(None)  # type: ignore[arg-type]


def test_invalid_evidence_item_is_rejected() -> None:
    with pytest.raises(MentalModelConfidenceError):
        estimate_mental_model_confidence(["invalid"])  # type: ignore[list-item]


def test_invalid_polarity_is_rejected() -> None:
    with pytest.raises(MentalModelConfidenceError):
        estimate_mental_model_confidence(
            [evidence(polarity="unknown")]
        )


def test_missing_polarity_is_rejected() -> None:
    item = evidence()
    del item["polarity"]

    with pytest.raises(MentalModelConfidenceError):
        estimate_mental_model_confidence([item])


def test_missing_governance_fields_are_not_treated_as_governed() -> None:
    item = evidence()
    del item["promoted"]

    result = estimate_mental_model_confidence([item])

    assert result.score == 0.0
    assert result.governed_evidence == 0


def test_confidence_does_not_mutate_model() -> None:
    model = {
        "model_id": "model-1",
        "evidence": [
            evidence(source_memory_id="memory-1"),
        ],
    }

    original = {
        "model_id": "model-1",
        "evidence": [
            evidence(source_memory_id="memory-1"),
        ],
    }

    confidence_from_model(model)

    assert model == original


def test_confidence_does_not_authorize_model() -> None:
    model = {
        "model_id": "model-1",
        "validation_status": "validated",
        "evidence": [
            evidence(source_memory_id="memory-1"),
        ],
    }

    result = confidence_from_model(model)

    assert result.score == 1.0
    assert model["validation_status"] == "validated"
    assert "promoted" not in model
    assert "promotion_status" not in model


def test_empty_evidence_is_valid_but_has_zero_confidence() -> None:
    result = estimate_mental_model_confidence([])

    assert result.score == 0.0
    assert result.supporting_evidence == 0
    assert result.contradicting_evidence == 0
    assert result.governed_evidence == 0
    assert result.provenance_complete is True

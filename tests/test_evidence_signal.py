from __future__ import annotations

import pytest

from src.retrieval.evidence_signal import build_evidence_signal


def test_empty_evidence_has_zero_quality():
    signal = build_evidence_signal(())

    assert signal.evidence_present is False
    assert signal.evidence_count == 0
    assert signal.observed_count == 0
    assert signal.inferred_count == 0
    assert signal.confidence is None
    assert signal.evidence_quality == 0.0


def test_observed_evidence_is_distinguished_from_inferred():
    signal = build_evidence_signal(
        (
            {"evidence_kind": "observed", "confidence": 1.0},
            {"evidence_kind": "inferred", "confidence": 0.5},
        )
    )

    assert signal.evidence_present is True
    assert signal.evidence_count == 2
    assert signal.observed_count == 1
    assert signal.inferred_count == 1
    assert signal.confidence == pytest.approx(0.75)
    assert signal.evidence_quality == pytest.approx(0.625)


def test_missing_confidence_is_preserved_as_unknown():
    signal = build_evidence_signal(
        (
            {"evidence_kind": "observed", "confidence": None},
        )
    )

    assert signal.confidence is None
    assert signal.evidence_quality == pytest.approx(0.5)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_invalid_confidence_is_rejected(value):
    with pytest.raises(ValueError):
        build_evidence_signal(
            (
                {"evidence_kind": "observed", "confidence": value},
            )
        )


def test_input_evidence_is_not_mutated():
    evidence = [
        {"evidence_kind": "observed", "confidence": 0.8},
    ]

    original = [dict(record) for record in evidence]

    build_evidence_signal(evidence)

    assert evidence == original

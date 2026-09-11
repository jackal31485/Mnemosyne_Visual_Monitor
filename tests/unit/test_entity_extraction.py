from __future__ import annotations

import pytest

from src.services.entity_extraction import (
    DeterministicEntityExtractor,
    EXTRACTION_METHOD,
)


def test_empty_content_returns_no_mentions():
    extractor = DeterministicEntityExtractor()

    assert extractor.extract("") == []
    assert extractor.extract("   ") == []


def test_non_string_content_is_rejected():
    extractor = DeterministicEntityExtractor()

    with pytest.raises(TypeError, match="string"):
        extractor.extract(None)  # type: ignore[arg-type]


def test_known_technology_is_extracted():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "Mnemosyne uses SQLite and FastAPI for the project."
    )

    values = {
        (item.mention_text, item.entity_type)
        for item in results
    }

    assert ("Mnemosyne", "technology") in values
    assert ("SQLite", "technology") in values
    assert ("FastAPI", "technology") in values


def test_extraction_is_deterministic():
    extractor = DeterministicEntityExtractor()

    content = (
        "Mnemosyne uses SQLite. "
        "FastAPI supports the Mnemosyne project."
    )

    first = extractor.extract(content)
    second = extractor.extract(content)

    assert first == second


def test_duplicate_mentions_are_collapsed():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "Mnemosyne uses SQLite. "
        "Later, Mnemosyne uses SQLite again."
    )

    keys = [
        (item.mention_text.casefold(), item.entity_type)
        for item in results
    ]

    assert len(keys) == len(set(keys))


def test_mentions_have_valid_confidence_and_method():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "Mnemosyne uses SQLite and FastAPI."
    )

    assert results

    for item in results:
        assert 0.0 <= item.confidence <= 1.0
        assert item.extraction_method == EXTRACTION_METHOD


def test_results_are_stably_sorted():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "FastAPI and SQLite support Mnemosyne."
    )

    keys = [
        (item.mention_text.casefold(), item.entity_type)
        for item in results
    ]

    assert keys == sorted(keys)

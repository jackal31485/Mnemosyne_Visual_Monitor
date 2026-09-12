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


def test_explicit_project_name_is_extracted():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "The Mnemosyne Visual Monitor project uses Python."
    )

    values = {
        (item.mention_text, item.entity_type)
        for item in results
    }

    assert ("Mnemosyne Visual Monitor", "project") in values
    assert ("Python", "technology") in values


def test_project_name_after_marker_is_extracted():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "The repository Mnemosyne Visual Monitor contains the browser UI."
    )

    values = {
        (item.mention_text, item.entity_type)
        for item in results
    }

    assert ("Mnemosyne Visual Monitor", "project") in values


def test_arbitrary_capitalized_phrases_are_not_projects():
    extractor = DeterministicEntityExtractor()

    content = (
        "Do NOT modify code yet. "
        "Implement Phase carefully. "
        "FULL ABSOLUTE PATHS are required. "
        "You MUST validate the repository. "
        "The Phase is still in progress."
    )

    results = extractor.extract(content)

    project_names = {
        item.mention_text
        for item in results
        if item.entity_type == "project"
    }

    assert project_names == set()


def test_real_data_project_noise_is_not_extracted():
    content = (
        "The LOCAL Ubuntu project is documented here. "
        "See the REPOSITORY LOCATION The project notes. "
        "The Current Project The status is unchanged. "
        "Mnemosyne_Visual_Monitor All configuration is tracked. "
        "Review the CURRENT REPOSITORY STATE The section. "
        "The Mnemosyne Visual Monitor project remains valid."
    )

    mentions = DeterministicEntityExtractor().extract(content)

    projects = {
        mention.mention_text
        for mention in mentions
        if mention.entity_type == "project"
    }

    assert projects == {"Mnemosyne Visual Monitor"}


def test_instruction_fragments_are_not_projects():
    extractor = DeterministicEntityExtractor()

    content = (
        "IMPORTANT SAFETY REQUIREMENT. "
        "CURRENT REPOSITORY STATE. "
        "Output ONLY the requested result. "
        "Before Phase completion, check the system."
    )

    results = extractor.extract(content)

    assert all(item.entity_type != "project" for item in results)


def test_extraction_is_deterministic():
    extractor = DeterministicEntityExtractor()

    content = (
        "The Mnemosyne Visual Monitor project uses SQLite. "
        "The Mnemosyne Visual Monitor project uses Python."
    )

    first = extractor.extract(content)
    second = extractor.extract(content)

    assert first == second


def test_duplicate_mentions_are_collapsed():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "The Mnemosyne Visual Monitor project uses SQLite. "
        "Later, the Mnemosyne Visual Monitor project uses SQLite again."
    )

    keys = [
        (item.mention_text.casefold(), item.entity_type)
        for item in results
    ]

    assert len(keys) == len(set(keys))


def test_mentions_have_valid_confidence_and_method():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "The Mnemosyne Visual Monitor project uses SQLite and FastAPI."
    )

    assert results

    for item in results:
        assert 0.0 <= item.confidence <= 1.0
        assert item.extraction_method == EXTRACTION_METHOD


def test_results_are_stably_sorted():
    extractor = DeterministicEntityExtractor()

    results = extractor.extract(
        "The Mnemosyne Visual Monitor project uses FastAPI and SQLite."
    )

    keys = [
        (item.mention_text.casefold(), item.entity_type)
        for item in results
    ]

    assert keys == sorted(keys)

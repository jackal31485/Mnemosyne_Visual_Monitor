from __future__ import annotations

import pytest

from src.domain.temporal_change import TemporalChangeAssertion
from src.domain.temporal_change_extractor import TemporalChangeExtractor


def make_extractor() -> TemporalChangeExtractor:
    return TemporalChangeExtractor()


def test_changed_from_to_is_extracted() -> None:
    results = make_extractor().extract(
        "The server changed from active to retired.",
        collective_entry_id=7,
        source_memory_id="memory-7",
        source_profile="athena",
    )

    assert len(results) == 1
    result = results[0]

    assert result.change_type == "state_change"
    assert result.previous_state == "active"
    assert result.new_state == "retired"
    assert result.subject_id == "memory-7"


def test_was_then_became_is_extracted() -> None:
    results = make_extractor().extract(
        "The project was planned, then became active.",
        collective_entry_id=8,
        source_memory_id="memory-8",
        source_profile="horus",
    )

    assert len(results) == 1
    assert results[0].previous_state == "planned"
    assert results[0].new_state == "active"


def test_became_is_an_explicit_activation() -> None:
    results = make_extractor().extract(
        "The service became operational.",
        collective_entry_id=9,
        source_memory_id="memory-9",
        source_profile="odin",
    )

    assert len(results) == 1
    assert results[0].change_type == "activation"
    assert results[0].previous_state is None
    assert results[0].new_state == "operational"


def test_replacement_is_extracted() -> None:
    results = make_extractor().extract(
        "Version 2 was replaced by Version 3.",
        collective_entry_id=10,
        source_memory_id="memory-10",
        source_profile="thoth",
    )

    assert len(results) == 1
    assert results[0].change_type == "replacement"
    assert results[0].new_state == "Version 3"


def test_no_explicit_change_means_no_assertion() -> None:
    results = make_extractor().extract(
        "The server is active and the project uses SQLite.",
        collective_entry_id=11,
        source_memory_id="memory-11",
        source_profile="athena",
    )

    assert results == []


def test_source_provenance_is_preserved() -> None:
    results = make_extractor().extract(
        "The service changed from beta to production.",
        collective_entry_id=12,
        source_memory_id="memory-12",
        source_profile="vulcan",
    )

    assert len(results) == 1
    result = results[0]

    assert result.collective_entry_id == 12
    assert result.source_memory_id == "memory-12"
    assert result.source_profile == "vulcan"
    assert result.extraction_method == "explicit_state_change_v1"


def test_duplicate_matches_are_deduplicated() -> None:
    results = make_extractor().extract(
        "The service became active. The service became active.",
        collective_entry_id=13,
        source_memory_id="memory-13",
        source_profile="athena",
    )

    assert len(results) == 1


def test_assertion_rejects_invalid_entry_id() -> None:
    with pytest.raises(ValueError):
        TemporalChangeAssertion(
            collective_entry_id=0,
            subject_type="memory",
            subject_id="memory-1",
            change_type="activation",
            previous_state=None,
            new_state="active",
            extraction_method="explicit_state_change_v1",
            source_memory_id="memory-1",
            source_profile="athena",
        )


def test_assertion_rejects_invalid_change_type() -> None:
    with pytest.raises(ValueError):
        TemporalChangeAssertion(
            collective_entry_id=1,
            subject_type="memory",
            subject_id="memory-1",
            change_type="inferred_change",
            previous_state=None,
            new_state="active",
            extraction_method="explicit_state_change_v1",
            source_memory_id="memory-1",
            source_profile="athena",
        )

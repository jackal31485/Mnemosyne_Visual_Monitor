from __future__ import annotations

import pytest

from src.services.relationship_extraction import (
    EntityMentionInput,
    RELATIONSHIP_EXTRACTION_METHOD,
    RELATIONSHIP_PREDICATES,
    extract_relationships,
)


def test_explicit_uses_relationship():
    results = extract_relationships(
        "Mnemosyne uses FastAPI.",
        ["Mnemosyne", "FastAPI"],
    )

    assert len(results) == 1
    result = results[0]

    assert result.subject_mention == "Mnemosyne"
    assert result.predicate == "uses"
    assert result.object_mention == "FastAPI"
    assert result.confidence == 0.95
    assert result.relationship_kind == "explicit"
    assert result.extraction_method == RELATIONSHIP_EXTRACTION_METHOD


@pytest.mark.parametrize(
    ("text", "predicate"),
    [
        ("Mnemosyne contains Hybrid Retrieval.", "contains"),
        ("Hybrid Retrieval is part of Mnemosyne.", "part_of"),
        ("Mnemosyne depends on SQLite.", "depends_on"),
        ("Mnemosyne was created by Hermes.", "created_by"),
        ("Mnemosyne is maintained by Hermes.", "maintained_by"),
        ("Athena is associated with Mnemosyne.", "associated_with"),
        ("Athena is related to Mnemosyne.", "related_to"),
        ("Observation is derived from Memory.", "derived_from"),
        ("Hermes has profile Athena.", "has_profile"),
        ("Mnemosyne mentions FastAPI.", "mentions"),
    ],
)
def test_supported_predicates(text, predicate):
    names = [
        "Mnemosyne",
        "Hybrid Retrieval",
        "SQLite",
        "Hermes",
        "Athena",
        "Observation",
        "Memory",
        "FastAPI",
    ]

    results = extract_relationships(text, names)

    assert len(results) == 1
    assert results[0].predicate == predicate
    assert results[0].relationship_kind == "explicit"


def test_all_phase_10_predicates_are_declared():
    assert set(RELATIONSHIP_PREDICATES) == {
        "uses",
        "contains",
        "part_of",
        "depends_on",
        "created_by",
        "maintained_by",
        "associated_with",
        "related_to",
        "derived_from",
        "has_profile",
        "mentions",
    }


def test_relationship_requires_known_subject_and_object():
    results = extract_relationships(
        "Mnemosyne uses FastAPI.",
        ["Mnemosyne"],
    )

    assert results == []


def test_unknown_text_does_not_create_relationships():
    results = extract_relationships(
        "A memory discusses a FastAPI route used by Mnemosyne.",
        ["Mnemosyne", "FastAPI"],
    )

    assert results == []


def test_inferred_relationships_are_not_returned_as_explicit():
    results = extract_relationships(
        "The evidence suggests Mnemosyne uses FastAPI.",
        ["Mnemosyne", "FastAPI"],
    )

    assert results == []


def test_case_insensitive_matching_preserves_supplied_spelling():
    results = extract_relationships(
        "mnemosyne uses fastapi.",
        [
            EntityMentionInput("Mnemosyne", "technology"),
            EntityMentionInput("FastAPI", "technology"),
        ],
    )

    assert len(results) == 1
    assert results[0].subject_mention == "Mnemosyne"
    assert results[0].object_mention == "FastAPI"


def test_duplicate_entity_mentions_do_not_duplicate_relationships():
    results = extract_relationships(
        "Mnemosyne uses FastAPI.",
        [
            "Mnemosyne",
            "mnemosyne",
            "FastAPI",
            "fastapi",
        ],
    )

    assert len(results) == 1


def test_multiple_relationships_are_sorted_deterministically():
    results = extract_relationships(
        "Mnemosyne uses SQLite. Mnemosyne uses FastAPI.",
        ["Mnemosyne", "SQLite", "FastAPI"],
    )

    assert [
        (result.subject_mention, result.predicate, result.object_mention)
        for result in results
    ] == [
        ("Mnemosyne", "uses", "FastAPI"),
        ("Mnemosyne", "uses", "SQLite"),
    ]


def test_entity_mention_metadata_is_not_embedded_in_result():
    results = extract_relationships(
        "Mnemosyne uses FastAPI.",
        [
            EntityMentionInput("Mnemosyne", "project"),
            EntityMentionInput("FastAPI", "technology"),
        ],
    )

    assert results[0].subject_mention == "Mnemosyne"
    assert results[0].object_mention == "FastAPI"
    assert not hasattr(results[0], "source_memory_id")
    assert not hasattr(results[0], "memory_content")


def test_empty_text_returns_empty():
    assert extract_relationships("", ["Mnemosyne", "FastAPI"]) == []


def test_non_string_text_is_rejected():
    with pytest.raises(TypeError):
        extract_relationships(None, ["Mnemosyne", "FastAPI"])


def test_whitespace_and_punctuation_are_normalized():
    results = extract_relationships(
        "Mnemosyne uses FastAPI!!!",
        ["Mnemosyne", "FastAPI"],
    )

    assert len(results) == 1
    assert results[0].subject_mention == "Mnemosyne"
    assert results[0].object_mention == "FastAPI"


def test_qualified_entity_mentions_are_preserved():
    results = extract_relationships(
        "Hermes uses agent-a:athena.",
        ["Hermes", "agent-a:athena"],
    )

    assert len(results) == 1
    assert results[0].object_mention == "agent-a:athena"

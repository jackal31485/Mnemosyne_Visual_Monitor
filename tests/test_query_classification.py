import pytest

from src.retrieval.query_classification import (
    QueryClassifier,
    QueryIntent,
    classify_query,
)


def test_normalizes_query_whitespace():
    result = classify_query("  sqlite   authoritative   datastore  ")

    assert result.normalized_query == "sqlite authoritative datastore"


def test_rejects_non_string_query():
    with pytest.raises(TypeError, match="query must be a string"):
        classify_query(None)


def test_rejects_empty_query():
    with pytest.raises(ValueError, match="query must not be empty"):
        classify_query("   ")


def test_defaults_unknown_query_to_semantic():
    result = classify_query(
        "How does Mnemosyne preserve evidence across memory retrieval?"
    )

    assert result.intent is QueryIntent.SEMANTIC
    assert result.signals == ()


def test_detects_lexical_query():
    result = classify_query(
        "Find the exact phrase SQLite is the authoritative datastore"
    )

    assert result.intent is QueryIntent.LEXICAL
    assert "lexical" in result.signals


def test_detects_temporal_query():
    result = classify_query(
        "What changed after September 2026?"
    )

    assert result.intent is QueryIntent.TEMPORAL
    assert "temporal" in result.signals


def test_detects_entity_query():
    result = classify_query(
        "Who is Athena?"
    )

    assert result.intent is QueryIntent.ENTITY
    assert "entity" in result.signals


def test_detects_relationship_query():
    result = classify_query(
        "What is the relationship between Athena and Mnemosyne?"
    )

    assert result.intent is QueryIntent.RELATIONSHIP
    assert "relationship" in result.signals


def test_multiple_signals_produce_hybrid_intent():
    result = classify_query(
        "Find the exact relationship between Athena and Mnemosyne after 2026"
    )

    assert result.intent is QueryIntent.HYBRID
    assert result.signals == (
        "lexical",
        "temporal",
        "relationship",
    )


def test_classification_is_deterministic():
    query = "What changed after September 2026?"

    first = classify_query(query)
    second = classify_query(query)

    assert first == second


def test_classifier_contains_no_authorization_state():
    result = classify_query("What is the relationship between Athena and Odin?")

    assert not hasattr(result, "authorized")
    assert not hasattr(result, "promoted")
    assert not hasattr(result, "revoked")


def test_normalize_is_available_as_explicit_contract():
    assert QueryClassifier.normalize(
        "  hello \n\t world  "
    ) == "hello world"

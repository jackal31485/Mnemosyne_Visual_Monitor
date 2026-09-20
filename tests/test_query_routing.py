import pytest

from src.retrieval.query_classification import (
    QueryClassification,
    QueryIntent,
)
from src.retrieval.query_routing import (
    QueryRouter,
    RetrievalChannel,
    RetrievalRoute,
    route_query,
)


@pytest.mark.parametrize(
    ("query", "intent", "channels"),
    [
        (
            "How does Mnemosyne preserve evidence?",
            QueryIntent.SEMANTIC,
            (RetrievalChannel.SEMANTIC,),
        ),
        (
            "Find the exact phrase SQLite authoritative datastore",
            QueryIntent.LEXICAL,
            (RetrievalChannel.LEXICAL,),
        ),
        (
            "What changed after September 2026?",
            QueryIntent.TEMPORAL,
            (
                RetrievalChannel.TEMPORAL,
                RetrievalChannel.SEMANTIC,
            ),
        ),
        (
            "Who is Athena?",
            QueryIntent.ENTITY,
            (
                RetrievalChannel.ENTITY,
                RetrievalChannel.SEMANTIC,
            ),
        ),
        (
            "What is the relationship between Athena and Mnemosyne?",
            QueryIntent.RELATIONSHIP,
            (
                RetrievalChannel.RELATIONSHIP,
                RetrievalChannel.ENTITY,
                RetrievalChannel.SEMANTIC,
            ),
        ),
        (
            "Find the exact relationship between Athena and Mnemosyne after 2026",
            QueryIntent.HYBRID,
            (
                RetrievalChannel.LEXICAL,
                RetrievalChannel.SEMANTIC,
                RetrievalChannel.TEMPORAL,
                RetrievalChannel.ENTITY,
                RetrievalChannel.RELATIONSHIP,
            ),
        ),
    ],
)
def test_route_query_maps_intent_to_expected_channels(
    query,
    intent,
    channels,
):
    result = route_query(query)

    assert isinstance(result, RetrievalRoute)
    assert result.intent is intent
    assert result.channels == channels


def test_route_preserves_normalized_query():
    result = route_query("  What   is   Athena?  ")

    assert result.normalized_query == "What is Athena?"


def test_route_preserves_classification_signals():
    result = route_query(
        "Find the exact relationship between Athena and Mnemosyne after 2026"
    )

    assert result.signals == (
        "lexical",
        "temporal",
        "relationship",
    )


def test_route_is_deterministic():
    query = "What changed after September 2026?"

    first = route_query(query)
    second = route_query(query)

    assert first == second


def test_router_rejects_invalid_classification():
    with pytest.raises(
        TypeError,
        match="classification must be a QueryClassification",
    ):
        QueryRouter.route("not a classification")


def test_router_rejects_unsupported_intent():
    classification = QueryClassification(
        intent="unsupported",  # type: ignore[arg-type]
        normalized_query="example",
        signals=(),
    )

    with pytest.raises(ValueError, match="unsupported query intent"):
        QueryRouter.route(classification)


def test_routing_has_no_authorization_semantics():
    result = route_query(
        "What is the relationship between Athena and Mnemosyne?"
    )

    assert not hasattr(result, "authorized")
    assert not hasattr(result, "promoted")
    assert not hasattr(result, "revoked")


def test_route_query_rejects_empty_query():
    with pytest.raises(ValueError, match="query must not be empty"):
        route_query("   ")


def test_route_does_not_mutate_classification():
    classification = QueryClassification(
        intent=QueryIntent.ENTITY,
        normalized_query="Who is Athena?",
        signals=("entity",),
    )

    result = QueryRouter.route(classification)

    assert classification.intent is QueryIntent.ENTITY
    assert classification.normalized_query == "Who is Athena?"
    assert classification.signals == ("entity",)
    assert result.intent is QueryIntent.ENTITY

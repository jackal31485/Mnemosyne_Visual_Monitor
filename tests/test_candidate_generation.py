from types import SimpleNamespace

import pytest

from src.retrieval.candidate_generation import (
    CandidateChannel,
    CandidateGenerationPolicy,
    CandidateGenerator,
    CandidateSet,
    generate_candidates,
)
from src.retrieval.query_classification import (
    QueryIntent,
    classify_query,
)
from src.retrieval.query_routing import (
    QueryRouter,
    RetrievalChannel,
    RetrievalRoute,
)


def result(entry_id):
    return SimpleNamespace(
        entry_id=entry_id,
        source_profile="Athena",
        origin_memory_id=f"memory-{entry_id}",
    )


def route(intent):
    return QueryRouter.route(
        classify_query(
            {
                QueryIntent.SEMANTIC: "How does Mnemosyne work?",
                QueryIntent.LEXICAL: "exact phrase keyword",
                QueryIntent.TEMPORAL: "when did this happen?",
                QueryIntent.ENTITY: "who is Athena?",
                QueryIntent.RELATIONSHIP: "what is the relationship?",
                QueryIntent.HYBRID: "exactly when is Athena related to this?",
            }[intent]
        )
    )


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (
            QueryIntent.SEMANTIC,
            (
                CandidateChannel.KEYWORD,
                CandidateChannel.SEMANTIC,
                CandidateChannel.GRAPH,
            ),
        ),
        (
            QueryIntent.LEXICAL,
            (
                CandidateChannel.KEYWORD,
                CandidateChannel.SEMANTIC,
                CandidateChannel.GRAPH,
            ),
        ),
        (
            QueryIntent.TEMPORAL,
            (
                CandidateChannel.KEYWORD,
                CandidateChannel.SEMANTIC,
                CandidateChannel.TEMPORAL,
                CandidateChannel.GRAPH,
            ),
        ),
        (
            QueryIntent.ENTITY,
            (
                CandidateChannel.KEYWORD,
                CandidateChannel.SEMANTIC,
                CandidateChannel.ENTITY,
                CandidateChannel.GRAPH,
            ),
        ),
        (
            QueryIntent.RELATIONSHIP,
            (
                CandidateChannel.KEYWORD,
                CandidateChannel.SEMANTIC,
                CandidateChannel.ENTITY,
                CandidateChannel.GRAPH,
            ),
        ),
        (
            QueryIntent.HYBRID,
            (
                CandidateChannel.KEYWORD,
                CandidateChannel.SEMANTIC,
                CandidateChannel.TEMPORAL,
                CandidateChannel.ENTITY,
                CandidateChannel.GRAPH,
            ),
        ),
    ],
)
def test_channels_for_route_preserves_broad_hybrid_behavior(
    intent,
    expected,
):
    assert CandidateGenerator.channels_for_route(route(intent)) == expected


def test_generate_deduplicates_ids_deterministically():
    generated = CandidateGenerator.generate(
        route(QueryIntent.SEMANTIC),
        keyword_results=[
            result(1),
            result(2),
        ],
        semantic_results=[
            result(2),
            result(3),
        ],
        graph_results=[
            result(3),
            result(4),
        ],
    )

    assert generated == CandidateSet(
        entry_ids=(1, 2, 3, 4),
        channels=(
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.GRAPH,
        ),
    )


def test_candidate_limit_is_enforced():
    generated = CandidateGenerator.generate(
        route(QueryIntent.SEMANTIC),
        keyword_results=[
            result(1),
            result(2),
            result(3),
        ],
        semantic_results=[
            result(4),
            result(5),
        ],
        policy=CandidateGenerationPolicy(candidate_limit=3),
    )

    assert generated.entry_ids == (1, 2, 3)


def test_empty_channels_produce_empty_candidates():
    generated = CandidateGenerator.generate(
        route(QueryIntent.SEMANTIC),
    )

    assert generated.entry_ids == ()


def test_results_are_not_mutated():
    first = result(1)
    second = result(2)

    before = vars(first).copy(), vars(second).copy()

    CandidateGenerator.generate(
        route(QueryIntent.SEMANTIC),
        keyword_results=[first],
        semantic_results=[second],
    )

    assert vars(first) == before[0]
    assert vars(second) == before[1]


def test_candidate_generator_has_no_governance_fields():
    fields = set(CandidateSet.__dataclass_fields__)

    assert "is_promoted" not in fields
    assert "is_revoked" not in fields
    assert "authorized" not in fields
    assert "profile" not in fields


def test_invalid_route_is_rejected():
    with pytest.raises(TypeError):
        CandidateGenerator.generate("not-a-route")


@pytest.mark.parametrize(
    "candidate_limit",
    [0, -1, True, False, "20", None],
)
def test_invalid_candidate_limit_is_rejected(candidate_limit):
    with pytest.raises(ValueError):
        CandidateGenerationPolicy(
            candidate_limit=candidate_limit,
        )


def test_invalid_result_entry_id_is_rejected():
    with pytest.raises(ValueError):
        CandidateGenerator.generate(
            route(QueryIntent.SEMANTIC),
            keyword_results=[
                SimpleNamespace(entry_id="not-an-id"),
            ],
        )


def test_wrapper_matches_generator():
    expected = CandidateGenerator.generate(
        route(QueryIntent.SEMANTIC),
        keyword_results=[
            result(1),
            result(2),
        ],
        semantic_results=[
            result(2),
            result(3),
        ],
        candidate_limit=2,
    )

    actual = generate_candidates(
        route(QueryIntent.SEMANTIC),
        keyword_results=[
            result(1),
            result(2),
        ],
        semantic_results=[
            result(2),
            result(3),
        ],
        candidate_limit=2,
    )

    assert actual == expected


def test_route_is_immutable():
    retrieval_route = RetrievalRoute(
        intent=QueryIntent.SEMANTIC,
        normalized_query="test",
        channels=(RetrievalChannel.SEMANTIC,),
        signals=(),
    )

    with pytest.raises(AttributeError):
        retrieval_route.intent = QueryIntent.LEXICAL

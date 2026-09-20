from dataclasses import dataclass

import pytest

from src.retrieval.retrieval_diagnostics import (
    RetrievalDiagnostics,
    build_retrieval_diagnostics,
)
from src.retrieval.reranker import RerankDiagnostics


@dataclass
class FakeResult:
    entry_id: int
    source_profile: str = "thoth"
    origin_memory_id: str = "memory-1"
    fused_rank: int = 1
    reranker_rank: int | None = None
    rank_change: int | None = None
    keyword_rank: int | None = 1
    semantic_rank: int | None = 2
    graph_rank: int | None = None
    temporal_rank: int | None = None
    entity_rank: int | None = None
    evidence_signal: object | None = None
    provenance: object | None = None


def test_builds_diagnostics_from_ranked_results_without_content():
    results = [
        FakeResult(
            entry_id=7,
            origin_memory_id="memory-7",
            provenance={"source": "collective"},
        ),
        FakeResult(
            entry_id=3,
            origin_memory_id="memory-3",
            fused_rank=2,
            keyword_rank=None,
            semantic_rank=1,
            evidence_signal=object(),
            provenance={"source": "collective"},
        ),
    ]

    diagnostics = build_retrieval_diagnostics(
        "SQLite authoritative datastore",
        results,
        requested_top_k=5,
        candidate_limit=20,
        reranking_enabled=False,
    )

    assert isinstance(diagnostics, RetrievalDiagnostics)
    assert diagnostics.query == "SQLite authoritative datastore"
    assert diagnostics.result_count == 2
    assert diagnostics.result_entry_ids == (7, 3)
    assert diagnostics.reranking_enabled is False

    assert diagnostics.result_diagnostics[0].entry_id == 7
    assert diagnostics.result_diagnostics[0].rank == 1
    assert diagnostics.result_diagnostics[0].provenance_present is True
    assert diagnostics.result_diagnostics[0].evidence_present is False

    assert diagnostics.result_diagnostics[1].entry_id == 3
    assert diagnostics.result_diagnostics[1].rank == 2
    assert diagnostics.result_diagnostics[1].evidence_present is True


def test_preserves_reranker_diagnostics_without_recomputing_them():
    reranker_diagnostics = RerankDiagnostics(
        candidate_limit=4,
        top_k=2,
        candidate_entry_ids=(1, 2, 3, 4),
        reranked_entry_ids=(3, 1),
        fused_scores=((1, 0.5), (2, 0.4), (3, 0.3), (4, 0.2)),
        reranker_scores=((3, 8.0), (1, 7.0)),
        rank_changes=((3, 2), (1, -1)),
    )

    diagnostics = build_retrieval_diagnostics(
        "query",
        [FakeResult(entry_id=3), FakeResult(entry_id=1, fused_rank=2)],
        requested_top_k=2,
        candidate_limit=4,
        reranking_enabled=True,
        reranker_diagnostics=reranker_diagnostics,
    )

    assert diagnostics.reranker_diagnostics is reranker_diagnostics


def test_evaluation_is_descriptive_and_uses_ranked_result_ids():
    diagnostics = build_retrieval_diagnostics(
        "query",
        [
            FakeResult(entry_id=8),
            FakeResult(entry_id=4, fused_rank=2),
            FakeResult(entry_id=2, fused_rank=3),
        ],
        requested_top_k=3,
        candidate_limit=10,
        reranking_enabled=False,
        relevant_entry_ids=[4, 2],
        evaluation_k=2,
    )

    assert diagnostics.evaluation is not None
    assert diagnostics.evaluation.retrieved_entry_ids == (8, 4, 2)
    assert diagnostics.evaluation.relevant_entry_ids == (4, 2)
    assert diagnostics.evaluation.evaluated_k == 2
    assert diagnostics.evaluation.precision_at_k == 0.5
    assert diagnostics.evaluation.recall_at_k == 0.5
    assert diagnostics.evaluation.mean_reciprocal_rank == pytest.approx(0.5)


def test_empty_results_are_safe_and_deterministic():
    diagnostics = build_retrieval_diagnostics(
        "query",
        [],
        requested_top_k=10,
        candidate_limit=20,
        reranking_enabled=False,
    )

    assert diagnostics.result_count == 0
    assert diagnostics.result_entry_ids == ()
    assert diagnostics.result_diagnostics == ()
    assert diagnostics.evaluation is None
    assert diagnostics.reranker_diagnostics is None


def test_evaluation_requires_relevant_ids():
    with pytest.raises(ValueError, match="relevant_entry_ids"):
        build_retrieval_diagnostics(
            "query",
            [],
            requested_top_k=10,
            candidate_limit=20,
            reranking_enabled=False,
            evaluation_k=5,
        )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", ValueError),
        ("   ", ValueError),
    ],
)
def test_rejects_empty_query(query, expected):
    with pytest.raises(expected):
        build_retrieval_diagnostics(
            query,
            [],
            requested_top_k=10,
            candidate_limit=20,
            reranking_enabled=False,
        )


def test_rejects_non_string_query():
    with pytest.raises(TypeError, match="query"):
        build_retrieval_diagnostics(
            123,
            [],
            requested_top_k=10,
            candidate_limit=20,
            reranking_enabled=False,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requested_top_k", 0),
        ("candidate_limit", 0),
        ("evaluation_k", 0),
    ],
)
def test_rejects_invalid_positive_limits(field, value):
    kwargs = {
        "requested_top_k": 10,
        "candidate_limit": 20,
        "reranking_enabled": False,
    }

    if field == "evaluation_k":
        kwargs["evaluation_k"] = value
        kwargs["relevant_entry_ids"] = [1]
    else:
        kwargs[field] = value

    with pytest.raises(ValueError):
        build_retrieval_diagnostics(
            "query",
            [],
            **kwargs,
        )


def test_diagnostics_do_not_consume_or_modify_result_order():
    results = [
        FakeResult(entry_id=5),
        FakeResult(entry_id=2, fused_rank=2),
    ]

    original_ids = [result.entry_id for result in results]

    diagnostics = build_retrieval_diagnostics(
        "query",
        results,
        requested_top_k=2,
        candidate_limit=5,
        reranking_enabled=False,
    )

    assert [result.entry_id for result in results] == original_ids
    assert diagnostics.result_entry_ids == (5, 2)


def test_diagnostics_do_not_expose_memory_content():
    results = [
        FakeResult(
            entry_id=1,
            origin_memory_id="memory-1",
            provenance={"source_profile": "thoth"},
        )
    ]

    diagnostics = build_retrieval_diagnostics(
        "query",
        results,
        requested_top_k=1,
        candidate_limit=1,
        reranking_enabled=False,
    )

    representation = repr(diagnostics)

    assert "memory content" not in representation.lower()
    assert "SQLite" not in representation
    assert "secret" not in representation.lower()

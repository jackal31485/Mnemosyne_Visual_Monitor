from dataclasses import replace

import pytest

from src.retrieval.explainability import (
    explain_fused,
    explain_reranked,
)
from src.retrieval.rank_fusion import FusedResult
from src.retrieval.reranker import RerankedResult


def make_fused(
    entry_id,
    *,
    keyword_rank=1,
    semantic_rank=2,
    graph_rank=3,
    temporal_rank=None,
    fused_score=0.5,
    provenance=None,
):
    return FusedResult(
        entry_id=entry_id,
        source_profile=f"profile-{entry_id}",
        origin_memory_id=f"memory-{entry_id}",
        fused_score=fused_score,
        keyword_rank=keyword_rank,
        semantic_rank=semantic_rank,
        graph_rank=graph_rank,
        temporal_rank=temporal_rank,
        keyword_contribution=0.10,
        semantic_contribution=0.20,
        graph_contribution=0.30,
        temporal_contribution=0.0,
        entity_rank=None,
        entity_contribution=0.0,
        provenance=provenance or [{"source": "collective"}],
    )


def make_reranked(
    entry_id,
    reranker_rank,
    *,
    fused_score=0.5,
    reranker_score=0.9,
    keyword_rank=1,
    semantic_rank=2,
    graph_rank=3,
    temporal_rank=None,
    provenance=None,
):
    return RerankedResult(
        entry_id=entry_id,
        source_profile=f"profile-{entry_id}",
        origin_memory_id=f"memory-{entry_id}",
        fused_score=fused_score,
        reranker_score=reranker_score,
        reranker_rank=reranker_rank,
        keyword_rank=keyword_rank,
        semantic_rank=semantic_rank,
        graph_rank=graph_rank,
        temporal_rank=temporal_rank,
        keyword_contribution=0.10,
        semantic_contribution=0.20,
        graph_contribution=0.30,
        temporal_contribution=0.0,
        entity_rank=None,
        entity_contribution=0.0,
        provenance=provenance or [{"source": "collective"}],
    )


def test_explain_fused_assigns_sequence_rank():
    results = [
        make_fused(10, fused_score=0.9),
        make_fused(20, fused_score=0.8),
        make_fused(30, fused_score=0.7),
    ]

    explanations = explain_fused(results)

    assert [item.entry_id for item in explanations] == [10, 20, 30]
    assert [item.fused_rank for item in explanations] == [1, 2, 3]


def test_explain_fused_does_not_infer_rank_from_score():
    results = [
        make_fused(10, fused_score=0.1),
        make_fused(20, fused_score=0.9),
    ]

    explanations = explain_fused(results)

    assert explanations[0].fused_rank == 1
    assert explanations[1].fused_rank == 2


def test_explain_fused_preserves_all_channel_metadata():
    result = make_fused(
        42,
        keyword_rank=4,
        semantic_rank=None,
        graph_rank=7,
        temporal_rank=9,
        provenance=[{"source_profile": "athena", "memory_id": "abc"}],
    )

    explanation = explain_fused([result])[0]

    assert explanation.keyword_rank == 4
    assert explanation.semantic_rank is None
    assert explanation.graph_rank == 7
    assert explanation.temporal_rank == 9

    assert explanation.keyword_contribution == 0.10
    assert explanation.semantic_contribution == 0.20
    assert explanation.graph_contribution == 0.30
    assert explanation.temporal_contribution == 0.0

    assert explanation.fused_score == result.fused_score
    assert explanation.provenance == result.provenance


def test_explain_fused_has_no_reranker_fields():
    explanation = explain_fused([make_fused(1)])[0]

    assert explanation.reranker_score is None
    assert explanation.reranker_rank is None
    assert explanation.rank_change is None


def test_explain_reranked_recovers_original_fused_rank():
    fused = [
        make_fused(10),
        make_fused(20),
        make_fused(30),
    ]

    reranked = [
        make_reranked(30, 1),
        make_reranked(10, 2),
        make_reranked(20, 3),
    ]

    explanations = explain_reranked(reranked, fused)

    assert [item.fused_rank for item in explanations] == [3, 1, 2]
    assert [item.reranker_rank for item in explanations] == [1, 2, 3]


def test_explain_reranked_calculates_rank_change():
    fused = [
        make_fused(10),
        make_fused(20),
        make_fused(30),
        make_fused(40),
    ]

    reranked = [
        make_reranked(40, 1),
        make_reranked(10, 2),
        make_reranked(30, 3),
        make_reranked(20, 4),
    ]

    explanations = explain_reranked(reranked, fused)

    assert [item.rank_change for item in explanations] == [3, -1, 0, -2]


def test_explain_reranked_preserves_reranker_score_and_fused_score():
    fused = [make_fused(10, fused_score=0.123)]
    reranked = [
        make_reranked(
            10,
            1,
            fused_score=0.123,
            reranker_score=4.567,
        )
    ]

    explanation = explain_reranked(reranked, fused)[0]

    assert explanation.fused_score == 0.123
    assert explanation.reranker_score == 4.567
    assert explanation.fused_rank == 1
    assert explanation.reranker_rank == 1
    assert explanation.rank_change == 0


def test_explain_reranked_preserves_identity_and_provenance():
    provenance = [
        {
            "source_profile": "athena",
            "memory_id": "memory-123",
        }
    ]

    fused = [make_fused(123, provenance=provenance)]
    reranked = [make_reranked(123, 1, provenance=provenance)]

    explanation = explain_reranked(reranked, fused)[0]

    assert explanation.entry_id == 123
    assert explanation.source_profile == "profile-123"
    assert explanation.origin_memory_id == "memory-123"
    assert explanation.provenance == provenance


def test_explain_reranked_rejects_inconsistent_reranker_rank():
    fused = [make_fused(10)]
    reranked = [make_reranked(10, 2)]

    with pytest.raises(ValueError, match="reranker_rank"):
        explain_reranked(reranked, fused)


def test_explain_reranked_rejects_unknown_entry():
    fused = [make_fused(10)]
    reranked = [make_reranked(99, 1)]

    with pytest.raises(ValueError, match="absent from fused results"):
        explain_reranked(reranked, fused)


def test_explain_reranked_is_deterministic():
    fused = [
        make_fused(10),
        make_fused(20),
    ]
    reranked = [
        make_reranked(20, 1),
        make_reranked(10, 2),
    ]

    first = explain_reranked(reranked, fused)
    second = explain_reranked(reranked, fused)

    assert first == second


def test_explain_fused_returns_empty_for_empty_input():
    assert explain_fused([]) == []


def test_explain_reranked_returns_empty_for_empty_input():
    assert explain_reranked([], []) == []

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import numpy as np
import pytest

from src.retrieval.hybrid_search import HybridRetrievalService
from src.retrieval.rank_fusion import FusedResult
from src.retrieval.reranker import RerankedResult


def make_result(
    entry_id,
    *,
    keyword_rank=None,
    semantic_rank=None,
    graph_rank=None,
    temporal_rank=None,
):
    return SimpleNamespace(
        entry_id=entry_id,
        source_profile="Athena",
        origin_memory_id=f"memory-{entry_id}",
        provenance=(("Athena", f"memory-{entry_id}", "2026-09-07"),),
        keyword_rank=keyword_rank,
        semantic_rank=semantic_rank,
        graph_rank=graph_rank,
        temporal_rank=temporal_rank,
    )


def make_fused(
    entry_id,
    score,
    *,
    keyword_rank=None,
    semantic_rank=None,
    graph_rank=None,
    temporal_rank=None,
):
    return FusedResult(
        entry_id=entry_id,
        source_profile="Athena",
        origin_memory_id=f"memory-{entry_id}",
        fused_score=score,
        keyword_rank=keyword_rank,
        semantic_rank=semantic_rank,
        graph_rank=graph_rank,
        temporal_rank=temporal_rank,
        keyword_contribution=(
            1.0 / (60 + keyword_rank)
            if keyword_rank is not None
            else 0.0
        ),
        semantic_contribution=(
            1.0 / (60 + semantic_rank)
            if semantic_rank is not None
            else 0.0
        ),
        graph_contribution=(
            1.0 / (60 + graph_rank)
            if graph_rank is not None
            else 0.0
        ),
        temporal_contribution=(
            1.0 / (60 + temporal_rank)
            if temporal_rank is not None
            else 0.0
        ),
        entity_rank=None,
        entity_contribution=0.0,
        provenance=(("Athena", f"memory-{entry_id}", "2026-09-07"),),
    )


def make_service(
    *,
    keyword_results=None,
    semantic_results=None,
    graph_results=None,
    temporal_results=None,
    fused_results=None,
    reranked_results=None,
):
    keyword = Mock()
    semantic = Mock()
    graph = Mock()
    temporal = Mock()
    fusion = Mock()
    encoder = Mock()
    reranker = Mock()

    keyword.search.return_value = keyword_results or []
    semantic.search.return_value = semantic_results or []
    graph.expand.return_value = graph_results or []
    temporal.search_by_recency.return_value = temporal_results or []
    temporal.search_by_event_date.return_value = temporal_results or []
    fusion.fuse.return_value = fused_results or []

    encoder.generate.return_value = np.zeros(
        384,
        dtype=np.float32,
    ).tobytes()

    reranker.rerank.return_value = reranked_results or []

    service = HybridRetrievalService(
        keyword_searcher=keyword,
        semantic_searcher=semantic,
        graph_searcher=graph,
        temporal_searcher=temporal,
        fusion=fusion,
        encoder=encoder,
        reranker=reranker,
    )

    return service, keyword, semantic, graph, temporal, fusion, encoder, reranker


def test_search_runs_keyword_semantic_graph_and_fusion():
    keyword_results = [
        make_result(1, keyword_rank=1),
        make_result(2, keyword_rank=2),
    ]
    semantic_results = [
        make_result(2, semantic_rank=1),
        make_result(3, semantic_rank=2),
    ]
    graph_results = [
        make_result(4, graph_rank=1),
    ]
    fused_results = [
        make_fused(
            2,
            0.04,
            keyword_rank=2,
            semantic_rank=1,
        ),
        make_fused(
            1,
            0.02,
            keyword_rank=1,
        ),
    ]

    (
        service,
        keyword,
        semantic,
        graph,
        _temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        semantic_results=semantic_results,
        graph_results=graph_results,
        fused_results=fused_results,
    )

    results = service.search(
        "test query",
        rerank=False,
    )

    keyword.search.assert_called_once_with(
        "test query",
        limit=20,
        profile=None,
    )

    encoder.generate.assert_called_once_with("test query")

    semantic.search.assert_called_once()
    query_vector = semantic.search.call_args.args[0]

    assert isinstance(query_vector, np.ndarray)
    assert query_vector.shape == (384,)

    graph.expand.assert_called_once_with(
        [1, 2, 3],
        limit_per_seed=4,
        profile=None,
    )

    fusion.fuse.assert_called_once_with(
        keyword_results=keyword_results,
        semantic_results=semantic_results,
        graph_results=graph_results,
        temporal_results=[],
    )

    assert [result.entry_id for result in results] == [2, 1]


def test_graph_seeds_are_unique_and_bounded():
    keyword_results = [
        make_result(1),
        make_result(2),
        make_result(3),
    ]
    semantic_results = [
        make_result(2),
        make_result(3),
        make_result(4),
    ]

    (
        service,
        _keyword,
        _semantic,
        graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        semantic_results=semantic_results,
        graph_results=[],
        fused_results=[],
    )

    service.search(
        "query",
        rerank=False,
        graph_seed_limit=3,
    )

    graph.expand.assert_called_once_with(
        [1, 2, 3],
        limit_per_seed=4,
        profile=None,
    )


def test_profile_is_forwarded_to_all_retrieval_channels():
    (
        service,
        keyword,
        semantic,
        graph,
        temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        keyword_results=[],
        semantic_results=[],
        graph_results=[],
        temporal_results=[],
        fused_results=[],
    )

    service.search(
        "query",
        profile="Horus",
        temporal_mode="recency",
        reference_time=datetime(2026, 9, 7, 12, 0, 0),
        rerank=False,
    )

    keyword.search.assert_called_once_with(
        "query",
        limit=20,
        profile="Horus",
    )

    semantic.search.assert_called_once()

    semantic_args, semantic_kwargs = semantic.search.call_args

    assert semantic_kwargs == {
        "top_k": 20,
        "profile": "Horus",
    }

    assert len(semantic_args) == 1

    np.testing.assert_array_equal(
        semantic_args[0],
        np.frombuffer(
            encoder.generate.return_value,
            dtype=np.float32,
        ),
    )

    graph.expand.assert_not_called()

    temporal.search_by_recency.assert_called_once_with(
        reference_time=datetime(2026, 9, 7, 12, 0, 0),
        limit=20,
        profile="Horus",
    )

    fusion.fuse.assert_called_once()


def test_event_date_temporal_mode_is_explicit():
    (
        service,
        _keyword,
        _semantic,
        _graph,
        temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        fused_results=[],
    )

    start = datetime(2026, 9, 1)
    end = datetime(2026, 9, 7)

    service.search(
        "query",
        temporal_mode="event_date",
        temporal_start=start,
        temporal_end=end,
        rerank=False,
    )

    temporal.search_by_event_date.assert_called_once_with(
        start,
        end,
        limit=20,
        profile=None,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temporal_mode": "invalid"},
        {
            "temporal_mode": "event_date",
            "temporal_start": datetime(2026, 9, 1),
        },
        {
            "temporal_mode": "recency",
            "temporal_start": datetime(2026, 9, 1),
        },
        {
            "temporal_mode": "recency",
            "reference_time": None,
        },
    ],
)
def test_invalid_temporal_configuration_is_rejected(kwargs):
    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service()

    if kwargs == {
        "temporal_mode": "recency",
        "reference_time": None,
    }:
        pytest.skip("None reference_time is valid and means current time")

    with pytest.raises(ValueError):
        service.search("query", **kwargs)


def test_reranking_is_optional():
    fused_results = [
        make_fused(1, 0.04, keyword_rank=1),
        make_fused(2, 0.03, semantic_rank=1),
    ]

    reranked_results = [
        RerankedResult(
            entry_id=2,
            source_profile="Athena",
            origin_memory_id="memory-2",
            fused_score=0.03,
            reranker_score=0.95,
            reranker_rank=1,
            keyword_rank=None,
            semantic_rank=1,
            graph_rank=None,
            temporal_rank=None,
            keyword_contribution=0.0,
            semantic_contribution=1.0 / 61,
            graph_contribution=0.0,
            temporal_contribution=0.0,
            entity_rank=None,
            entity_contribution=0.0,
            provenance=(("Athena", "memory-2", "2026-09-07"),),
        ),
    ]

    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        reranker,
    ) = make_service(
        fused_results=fused_results,
        reranked_results=reranked_results,
    )

    results = service.search(
        "query",
        rerank=True,
        top_k=1,
        candidate_limit=20,
    )

    reranker.rerank.assert_called_once_with(
        "query",
        fused_results,
        candidate_limit=20,
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].entry_id == 2
    assert results[0].reranker_score == 0.95
    assert results[0].reranker_rank == 1
    assert results[0].fused_rank == 2
    assert results[0].rank_change == 1


def test_reranking_can_be_disabled_even_when_configured():
    fused_results = [
        make_fused(1, 0.04, keyword_rank=1),
    ]

    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        reranker,
    ) = make_service(
        fused_results=fused_results,
    )

    results = service.search(
        "query",
        rerank=False,
    )

    reranker.rerank.assert_not_called()

    assert len(results) == 1
    assert results[0].entry_id == 1
    assert results[0].fused_rank == 1
    assert results[0].reranker_score is None


def test_empty_retrieval_returns_empty_results():
    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        fusion,
        _encoder,
        _reranker,
    ) = make_service(
        fused_results=[],
    )

    results = service.search(
        "query",
        rerank=False,
    )

    fusion.fuse.assert_called_once()
    assert results == []


def test_blank_query_returns_without_calling_retrievers():
    (
        service,
        keyword,
        semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service()

    assert service.search("   ") == []

    keyword.search.assert_not_called()
    semantic.search.assert_not_called()


def test_entity_channel_flows_through_hybrid_pipeline():
    from src.retrieval.entity_search import EntityResult

    entity_searcher = Mock()
    entity_result = EntityResult(
        entry_id=7,
        source_profile="Athena",
        origin_memory_id="entity-memory-7",
        entity_score=1.0,
        provenance=(
            ("Athena", "entity-memory-7", "2026-09-07"),
        ),
    )
    entity_searcher.search.return_value = [entity_result]

    fused_result = make_fused(
        7,
        1.0 / 61.0,
    )
    fused_result = FusedResult(
        entry_id=fused_result.entry_id,
        source_profile=fused_result.source_profile,
        origin_memory_id="entity-memory-7",
        fused_score=fused_result.fused_score,
        keyword_rank=fused_result.keyword_rank,
        semantic_rank=fused_result.semantic_rank,
        graph_rank=fused_result.graph_rank,
        temporal_rank=fused_result.temporal_rank,
        entity_rank=1,
        keyword_contribution=fused_result.keyword_contribution,
        semantic_contribution=fused_result.semantic_contribution,
        graph_contribution=fused_result.graph_contribution,
        temporal_contribution=fused_result.temporal_contribution,
        entity_contribution=1.0 / 61.0,
        provenance=fused_result.provenance,
    )

    (
        service,
        keyword,
        semantic,
        graph,
        temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        fused_results=[fused_result],
    )

    service.entity_searcher = entity_searcher

    results = service.search(
        "Mnemosyne",
        profile="Athena",
        rerank=False,
    )

    entity_searcher.search.assert_called_once_with(
        "Mnemosyne",
        limit=20,
        profile="Athena",
    )

    fusion.fuse.assert_called_once_with(
        keyword_results=[],
        semantic_results=[],
        graph_results=[],
        temporal_results=[],
        entity_results=[entity_result],
    )

    assert len(results) == 1
    assert results[0].entry_id == 7
    assert results[0].source_profile == "Athena"
    assert results[0].origin_memory_id == "entity-memory-7"
    assert results[0].entity_rank == 1
    assert results[0].entity_contribution == pytest.approx(1.0 / 61.0)


def test_search_classifies_and_routes_query_without_changing_governed_pipeline(
    monkeypatch,
):
    from src.retrieval import hybrid_search as hybrid_search_module

    route = Mock()
    route.intent = "relationship"
    route.normalized_query = (
        "What is the relationship between Athena and Mnemosyne?"
    )
    route.channels = ()
    route.signals = ("relationship",)

    route_query = Mock(return_value=route)
    monkeypatch.setattr(
        hybrid_search_module.QueryRouter,
        "route_query",
        route_query,
    )

    (
        service,
        keyword,
        semantic,
        graph,
        temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        keyword_results=[],
        semantic_results=[],
        graph_results=[],
        temporal_results=[],
        fused_results=[],
    )

    service.search(
        "What is the relationship between Athena and Mnemosyne?",
        rerank=False,
    )

    route_query.assert_called_once_with(
        "What is the relationship between Athena and Mnemosyne?"
    )

    keyword.search.assert_called_once_with(
        "What is the relationship between Athena and Mnemosyne?",
        limit=20,
        profile=None,
    )

    semantic.search.assert_called_once()
    graph.expand.assert_not_called()
    temporal.search_by_recency.assert_not_called()
    temporal.search_by_event_date.assert_not_called()

    fusion.fuse.assert_called_once()


def test_semantic_query_preserves_existing_hybrid_candidate_behavior():
    (
        service,
        keyword,
        semantic,
        graph,
        _temporal,
        fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=[make_result(1, keyword_rank=1)],
        semantic_results=[make_result(2, semantic_rank=1)],
        graph_results=[make_result(3, graph_rank=1)],
        fused_results=[],
    )

    service.search(
        "How does Mnemosyne preserve evidence?",
        rerank=False,
    )

    keyword.search.assert_called_once()
    semantic.search.assert_called_once()
    graph.expand.assert_called_once_with(
        [1, 2],
        limit_per_seed=4,
        profile=None,
    )

    fusion.fuse.assert_called_once()


def test_route_integration_does_not_change_profile_boundary():
    (
        service,
        keyword,
        semantic,
        graph,
        _temporal,
        fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=[],
        semantic_results=[],
        graph_results=[],
        fused_results=[],
    )

    service.search(
        "Who is Athena?",
        profile="Horus",
        rerank=False,
    )

    keyword.search.assert_called_once_with(
        "Who is Athena?",
        limit=20,
        profile="Horus",
    )

    semantic_args, semantic_kwargs = semantic.search.call_args

    assert semantic_kwargs == {
        "top_k": 20,
        "profile": "Horus",
    }

    graph.expand.assert_not_called()
    fusion.fuse.assert_called_once()


def test_evidence_signal_is_attached_to_governed_candidate():
    keyword_results = [
        make_result(1, keyword_rank=1),
    ]

    fused_results = [
        make_fused(
            1,
            0.02,
            keyword_rank=1,
        ),
    ]

    evidence_dao = Mock()
    evidence_dao.list.return_value = [
        {
            "temporal_evidence_id": "te-1",
            "collective_entry_id": 1,
            "evidence_kind": "observed",
            "confidence": 0.9,
            "source_profile": "Athena",
            "source_memory_id": "memory-1",
        },
        {
            "temporal_evidence_id": "te-2",
            "collective_entry_id": 1,
            "evidence_kind": "inferred",
            "confidence": 0.7,
            "source_profile": "Athena",
            "source_memory_id": "memory-1",
        },
    ]

    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        fused_results=fused_results,
    )

    service.evidence_dao = evidence_dao

    results = service.search(
        "test query",
        rerank=False,
    )

    assert len(results) == 1

    result = results[0]

    assert result.entry_id == 1
    assert result.evidence_signal is not None
    assert result.evidence_signal.evidence_present is True
    assert result.evidence_signal.evidence_count == 2
    assert result.evidence_signal.observed_count == 1
    assert result.evidence_signal.inferred_count == 1
    assert result.evidence_signal.confidence == pytest.approx(0.8)
    assert result.evidence_signal.evidence_quality == pytest.approx(0.65)

    evidence_dao.list.assert_called_once_with(
        collective_entry_id=1,
        source_profile="Athena",
    )


def test_evidence_lookup_preserves_source_profile_isolation():
    keyword_results = [
        make_result(1, keyword_rank=1),
    ]

    fused_results = [
        make_fused(
            1,
            0.02,
            keyword_rank=1,
        ),
    ]

    evidence_dao = Mock()
    evidence_dao.list.return_value = [
        {
            "temporal_evidence_id": "te-athena",
            "collective_entry_id": 1,
            "evidence_kind": "observed",
            "confidence": 1.0,
            "source_profile": "Athena",
            "source_memory_id": "memory-1",
        },
    ]

    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        fused_results=fused_results,
    )

    service.evidence_dao = evidence_dao

    results = service.search(
        "test query",
        profile="Athena",
        rerank=False,
    )

    assert [result.entry_id for result in results] == [1]

    evidence_dao.list.assert_called_once_with(
        collective_entry_id=1,
        source_profile="Athena",
    )


def test_evidence_cannot_expand_candidate_universe():
    keyword_results = [
        make_result(1, keyword_rank=1),
    ]

    fused_results = [
        make_fused(
            1,
            0.02,
            keyword_rank=1,
        ),
    ]

    evidence_dao = Mock()
    evidence_dao.list.return_value = [
        {
            "temporal_evidence_id": "te-extra",
            "collective_entry_id": 999,
            "evidence_kind": "observed",
            "confidence": 1.0,
            "source_profile": "Athena",
            "source_memory_id": "memory-999",
        },
    ]

    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        fused_results=fused_results,
    )

    service.evidence_dao = evidence_dao

    results = service.search(
        "test query",
        rerank=False,
    )

    assert [result.entry_id for result in results] == [1]
    assert all(result.entry_id != 999 for result in results)

    evidence_dao.list.assert_called_once_with(
        collective_entry_id=1,
        source_profile="Athena",
    )


def test_evidence_signals_do_not_change_fused_result_order_or_provenance():
    keyword_results = [
        make_result(1, keyword_rank=1),
        make_result(2, keyword_rank=2),
    ]

    fused_results = [
        make_fused(
            1,
            0.04,
            keyword_rank=1,
        ),
        make_fused(
            2,
            0.03,
            keyword_rank=2,
        ),
    ]

    (
        baseline_service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        fused_results=fused_results,
    )

    baseline = baseline_service.search(
        "test query",
        rerank=False,
    )

    evidence_dao = Mock()
    evidence_dao.list.side_effect = [
        [
            {
                "temporal_evidence_id": "te-1",
                "collective_entry_id": 1,
                "evidence_kind": "observed",
                "confidence": 1.0,
                "source_profile": "Athena",
                "source_memory_id": "memory-1",
            },
        ],
        [
            {
                "temporal_evidence_id": "te-2",
                "collective_entry_id": 2,
                "evidence_kind": "inferred",
                "confidence": 0.2,
                "source_profile": "Athena",
                "source_memory_id": "memory-2",
            },
        ],
    ]

    (
        evidence_service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        fused_results=fused_results,
    )

    evidence_service.evidence_dao = evidence_dao

    enriched = evidence_service.search(
        "test query",
        rerank=False,
    )

    assert [result.entry_id for result in enriched] == [
        result.entry_id for result in baseline
    ]

    assert [result.fused_score for result in enriched] == [
        result.fused_score for result in baseline
    ]

    assert [result.fused_rank for result in enriched] == [
        result.fused_rank for result in baseline
    ]

    assert [result.provenance for result in enriched] == [
        result.provenance for result in baseline
    ]

    assert enriched[0].evidence_signal is not None
    assert enriched[1].evidence_signal is not None


def test_reranking_preserves_evidence_signal_metadata():
    keyword_results = [
        make_result(1, keyword_rank=1),
    ]

    fused_results = [
        make_fused(1, 0.04, keyword_rank=1),
    ]

    reranked_results = [
        RerankedResult(
            entry_id=1,
            source_profile="Athena",
            origin_memory_id="memory-1",
            fused_score=0.04,
            reranker_score=0.95,
            reranker_rank=1,
            keyword_rank=1,
            semantic_rank=None,
            graph_rank=None,
            temporal_rank=None,
            keyword_contribution=0.01,
            semantic_contribution=0.0,
            graph_contribution=0.0,
            temporal_contribution=0.0,
            entity_rank=None,
            entity_contribution=0.0,
            provenance=(("Athena", "memory-1", "2026-09-07"),),
        ),
    ]

    (
        service,
        _keyword,
        _semantic,
        _graph,
        _temporal,
        _fusion,
        _encoder,
        _reranker,
    ) = make_service(
        keyword_results=keyword_results,
        fused_results=fused_results,
        reranked_results=reranked_results,
    )

    from src.retrieval.evidence_signal import EvidenceSignal

    service.evidence_dao = MagicMock()
    service.evidence_dao.list.return_value = [
        {
            "evidence_kind": "observed",
            "confidence": 1.0,
        },
    ]

    results = service.search(
        "query",
        rerank=True,
        top_k=1,
        candidate_limit=20,
    )

    assert len(results) == 1
    assert results[0].evidence_signal == EvidenceSignal(
        evidence_present=True,
        evidence_count=1,
        observed_count=1,
        inferred_count=0,
        confidence=1.0,
        evidence_quality=1.0,
    )


def test_non_latin_query_skips_unsupported_semantic_retrieval():
    (
        service,
        keyword,
        semantic,
        _graph,
        _temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        keyword_results=[make_result(1, keyword_rank=1)],
        semantic_results=[],
        fused_results=[],
    )

    service.search(
        "メモリの検索",
        rerank=False,
    )

    keyword.search.assert_called_once_with(
        "メモリの検索",
        limit=20,
        profile=None,
    )
    encoder.generate.assert_not_called()
    semantic.search.assert_not_called()
    fusion.fuse.assert_called_once()


def test_mixed_script_query_skips_unsupported_semantic_retrieval():
    (
        service,
        keyword,
        semantic,
        _graph,
        _temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        keyword_results=[make_result(1, keyword_rank=1)],
        semantic_results=[],
        fused_results=[],
    )

    service.search(
        "Mnemosyne メモリ",
        rerank=False,
    )

    keyword.search.assert_called_once_with(
        "Mnemosyne メモリ",
        limit=20,
        profile=None,
    )
    encoder.generate.assert_not_called()
    semantic.search.assert_not_called()
    fusion.fuse.assert_called_once()


def test_latin_query_retains_existing_semantic_retrieval():
    (
        service,
        keyword,
        semantic,
        _graph,
        _temporal,
        fusion,
        encoder,
        _reranker,
    ) = make_service(
        keyword_results=[],
        semantic_results=[],
        fused_results=[],
    )

    service.search(
        "How does Mnemosyne preserve evidence?",
        rerank=False,
    )

    keyword.search.assert_called_once()
    encoder.generate.assert_called_once_with(
        "How does Mnemosyne preserve evidence?"
    )
    semantic.search.assert_called_once()
    fusion.fuse.assert_called_once()

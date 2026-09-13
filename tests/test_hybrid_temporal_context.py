from datetime import datetime

from src.retrieval.hybrid_search import HybridRetrievalService


class FakeExplanation:
    def __init__(self, entry_id):
        self.entry_id = entry_id
        self.source_profile = "test"
        self.origin_memory_id = f"memory-{entry_id}"
        self.fused_score = 1.0
        self.fused_rank = 1
        self.reranker_score = None
        self.reranker_rank = None
        self.rank_change = None
        self.keyword_rank = None
        self.keyword_contribution = 0.0
        self.semantic_rank = 1
        self.semantic_contribution = 1.0
        self.graph_rank = None
        self.graph_contribution = 0.0
        self.temporal_rank = 1
        self.temporal_contribution = 1.0
        self.entity_rank = None
        self.entity_contribution = 0.0
        self.provenance = object()


def test_hybrid_result_without_temporal_context_is_explicit():
    result = HybridRetrievalService._to_hybrid_results(
        [FakeExplanation(42)],
        temporal_contexts={},
    )[0]

    assert result.entry_id == 42
    assert result.temporal_query_relevant is False
    assert result.temporal_query_score == 0.0
    assert result.temporal_query_context is None


def test_hybrid_result_preserves_temporal_context():
    from src.retrieval.temporal_query_scoring import (
        TemporalQueryScore,
    )
    from src.retrieval.temporal_result_context import (
        build_temporal_result_context,
    )

    start = datetime(2026, 9, 1)
    end = datetime(2026, 9, 10, 23, 59, 59)

    context = build_temporal_result_context(
        query_start=start,
        query_end=end,
        temporal_score=TemporalQueryScore(
            score=1.0,
            overlaps=True,
            within_query_window=True,
            date_source="event_date",
        ),
    )

    result = HybridRetrievalService._to_hybrid_results(
        [FakeExplanation(42)],
        temporal_contexts={42: context},
    )[0]

    assert result.temporal_query_relevant is True
    assert result.temporal_query_score == 1.0
    assert result.temporal_query_context == context

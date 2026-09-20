from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domain.memory_gateway import InMemoryMemoryGateway
from src.retrieval.rank_fusion import FusedResult
from src.retrieval.reranker import Reranker


@dataclass
class FakeCrossEncoder:
    scores: list[float]
    received_pairs: list[tuple[str, str]] | None = None

    def predict(self, pairs):
        self.received_pairs = list(pairs)
        return self.scores


def fused(entry_id: int, origin: str | None = None) -> FusedResult:
    origin = origin or f"memory-{entry_id}"

    return FusedResult(
        entry_id=entry_id,
        source_profile="athena",
        origin_memory_id=origin,
        fused_score=1.0 / entry_id,
        keyword_rank=entry_id,
        semantic_rank=None,
        graph_rank=None,
        temporal_rank=None,
        keyword_contribution=0.01,
        semantic_contribution=0.0,
        graph_contribution=0.0,
        temporal_contribution=0.0,
        entity_rank=None,
        entity_contribution=0.0,
        provenance=(("athena", origin, "created"),),
    )


def gateway_for(*entries: FusedResult) -> InMemoryMemoryGateway:
    gateway = InMemoryMemoryGateway()

    for entry in entries:
        gateway.add_memory(
            entry.source_profile,
            entry.origin_memory_id,
            f"content for {entry.entry_id}",
        )

    return gateway


def test_reranks_candidates_by_crossencoder_score() -> None:
    candidates = [fused(1), fused(2), fused(3)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.1, 0.9, 0.3])

    results = Reranker(encoder, gateway).rerank(
        "test query",
        candidates,
    )

    assert [result.entry_id for result in results] == [2, 3, 1]
    assert [result.reranker_rank for result in results] == [1, 2, 3]
    assert [result.reranker_score for result in results] == [
        0.9,
        0.3,
        0.1,
    ]


def test_query_and_content_pairs_are_sent_to_encoder() -> None:
    candidates = [fused(1), fused(2)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.2, 0.8])

    Reranker(encoder, gateway).rerank(
        "my query",
        candidates,
    )

    assert encoder.received_pairs == [
        ("my query", "content for 1"),
        ("my query", "content for 2"),
    ]


def test_candidate_limit_bounds_encoder_work() -> None:
    candidates = [fused(1), fused(2), fused(3)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.2, 0.8])

    results = Reranker(encoder, gateway).rerank(
        "query",
        candidates,
        candidate_limit=2,
    )

    assert len(results) == 2
    assert encoder.received_pairs == [
        ("query", "content for 1"),
        ("query", "content for 2"),
    ]


def test_top_k_limits_final_results() -> None:
    candidates = [fused(1), fused(2), fused(3)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.1, 0.9, 0.3])

    results = Reranker(encoder, gateway).rerank(
        "query",
        candidates,
        top_k=2,
    )

    assert [result.entry_id for result in results] == [2, 3]


def test_equal_scores_use_entry_id_as_deterministic_tie_break() -> None:
    candidates = [fused(3), fused(1), fused(2)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.5, 0.5, 0.5])

    results = Reranker(encoder, gateway).rerank(
        "query",
        candidates,
    )

    assert [result.entry_id for result in results] == [1, 2, 3]


def test_rrf_metadata_and_provenance_are_preserved() -> None:
    candidate = fused(42, "source-42")
    gateway = gateway_for(candidate)
    encoder = FakeCrossEncoder([0.75])

    result = Reranker(encoder, gateway).rerank(
        "query",
        [candidate],
    )[0]

    assert result.entry_id == 42
    assert result.source_profile == "athena"
    assert result.origin_memory_id == "source-42"
    assert result.fused_score == candidate.fused_score
    assert result.keyword_rank == candidate.keyword_rank
    assert result.keyword_contribution == candidate.keyword_contribution
    assert result.provenance == candidate.provenance
    assert result.reranker_score == pytest.approx(0.75)
    assert result.reranker_rank == 1


def test_empty_candidates_return_empty_result() -> None:
    gateway = InMemoryMemoryGateway()
    encoder = FakeCrossEncoder([])

    assert Reranker(encoder, gateway).rerank(
        "query",
        [],
    ) == []


def test_missing_source_memory_is_rejected() -> None:
    candidate = fused(1)
    gateway = InMemoryMemoryGateway()
    encoder = FakeCrossEncoder([0.5])

    with pytest.raises(KeyError):
        Reranker(encoder, gateway).rerank(
            "query",
            [candidate],
        )


def test_invalid_limits_are_rejected() -> None:
    candidate = fused(1)
    gateway = gateway_for(candidate)
    encoder = FakeCrossEncoder([0.5])
    reranker = Reranker(encoder, gateway)

    with pytest.raises(ValueError):
        reranker.rerank("query", [candidate], candidate_limit=0)

    with pytest.raises(ValueError):
        reranker.rerank("query", [candidate], top_k=0)


def test_empty_query_is_rejected() -> None:
    candidate = fused(1)
    gateway = gateway_for(candidate)
    encoder = FakeCrossEncoder([0.5])

    with pytest.raises(ValueError):
        Reranker(encoder, gateway).rerank(
            "",
            [candidate],
        )


def test_encoder_score_count_must_match_candidates() -> None:
    candidates = [fused(1), fused(2)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.5])

    with pytest.raises(ValueError, match="different number"):
        Reranker(encoder, gateway).rerank(
            "query",
            candidates,
        )


def test_non_finite_encoder_score_is_rejected() -> None:
    candidate = fused(1)
    gateway = gateway_for(candidate)
    encoder = FakeCrossEncoder([float("nan")])

    with pytest.raises(ValueError, match="non-finite"):
        Reranker(encoder, gateway).rerank(
            "query",
            [candidate],
        )


def test_rerank_diagnostics_describe_bounded_ranking():
    candidates = [fused(1), fused(2), fused(3)]
    gateway = gateway_for(*candidates)
    encoder = FakeCrossEncoder([0.1, 0.9])

    reranker = Reranker(encoder, gateway)

    results = reranker.rerank(
        "query",
        candidates,
        candidate_limit=2,
        top_k=2,
    )

    assert [result.entry_id for result in results] == [2, 1]

    assert reranker.last_diagnostics.candidate_limit == 2
    assert reranker.last_diagnostics.top_k == 2
    assert reranker.last_diagnostics.candidate_entry_ids == (1, 2)
    assert reranker.last_diagnostics.reranked_entry_ids == (2, 1)
    assert reranker.last_diagnostics.fused_scores == (
        (1, candidates[0].fused_score),
        (2, candidates[1].fused_score),
    )
    assert reranker.last_diagnostics.reranker_scores == (
        (2, 0.9),
        (1, 0.1),
    )
    assert reranker.last_diagnostics.rank_changes == (
        (2, 1),
        (1, -1),
    )


def test_rerank_diagnostics_are_empty_for_empty_candidates():
    reranker = Reranker(
        FakeCrossEncoder([]),
        InMemoryMemoryGateway(),
    )

    assert reranker.rerank("query", []) == []

    assert reranker.last_diagnostics.candidate_entry_ids == ()
    assert reranker.last_diagnostics.reranked_entry_ids == ()
    assert reranker.last_diagnostics.fused_scores == ()
    assert reranker.last_diagnostics.reranker_scores == ()
    assert reranker.last_diagnostics.rank_changes == ()

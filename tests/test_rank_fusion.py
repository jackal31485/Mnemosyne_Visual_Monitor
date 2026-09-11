from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.retrieval.graph_search import GraphResult
from src.retrieval.keyword_search import KeywordResult
from src.retrieval.semantic_search import SemanticResult
from src.retrieval.temporal_search import TemporalResult


@dataclass(frozen=True)
class DummyResult:
    entry_id: int
    source_profile: str = "athena"
    origin_memory_id: str = "memory"
    provenance: tuple = ()


def keyword(entry_id: int, origin: str | None = None) -> KeywordResult:
    return KeywordResult(
        entry_id=entry_id,
        source_profile="athena",
        origin_memory_id=origin or f"memory-{entry_id}",
        score=-1.0,
        provenance=[{"source_profile": "athena", "origin_memory_id": origin or f"memory-{entry_id}"}],
    )


def semantic(entry_id: int, origin: str | None = None) -> SemanticResult:
    return SemanticResult(
        entry_id=entry_id,
        source_profile="athena",
        origin_memory_id=origin or f"memory-{entry_id}",
        semantic_score=0.9,
        provenance=(("athena", origin or f"memory-{entry_id}", "created"),),
    )


def graph(entry_id: int, origin: str | None = None) -> GraphResult:
    return GraphResult(
        entry_id=entry_id,
        source_profile="athena",
        origin_memory_id=origin or f"memory-{entry_id}",
        graph_score=0.8,
        provenance=(("athena", origin or f"memory-{entry_id}", "created"),),
    )


def temporal(entry_id: int, origin: str | None = None) -> TemporalResult:
    from datetime import datetime

    return TemporalResult(
        entry_id=entry_id,
        source_profile="athena",
        origin_memory_id=origin or f"memory-{entry_id}",
        temporal_score=0.7,
        memory_date=datetime(2026, 9, 1),
        date_source="event_date",
        event_date_precision="day",
        provenance=(("athena", origin or f"memory-{entry_id}", "created"),),
    )


def test_single_channel_uses_rank_one_rrf_score() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion(k=60).fuse(
        keyword_results=[keyword(1)],
    )[0]

    assert result.entry_id == 1
    assert result.keyword_rank == 1
    assert result.semantic_rank is None
    assert result.graph_rank is None
    assert result.temporal_rank is None

    expected = 1.0 / 61.0

    assert result.keyword_contribution == pytest.approx(expected)
    assert result.fused_score == pytest.approx(expected)


def test_multiple_channels_accumulate_rrf_contributions() -> None:
    from src.retrieval.rank_fusion import RankFusion

    results = RankFusion(k=60).fuse(
        keyword_results=[keyword(1)],
        semantic_results=[semantic(1)],
        graph_results=[graph(1)],
        temporal_results=[temporal(1)],
    )

    result = results[0]

    expected = 4.0 / 61.0

    assert result.keyword_rank == 1
    assert result.semantic_rank == 1
    assert result.graph_rank == 1
    assert result.temporal_rank == 1

    assert result.keyword_contribution == pytest.approx(1.0 / 61.0)
    assert result.semantic_contribution == pytest.approx(1.0 / 61.0)
    assert result.graph_contribution == pytest.approx(1.0 / 61.0)
    assert result.temporal_contribution == pytest.approx(1.0 / 61.0)
    assert result.fused_score == pytest.approx(expected)


def test_missing_channels_contribute_zero() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion(k=60).fuse(
        keyword_results=[keyword(1)],
        semantic_results=[semantic(2)],
    )

    by_id = {item.entry_id: item for item in result}

    assert by_id[1].fused_score == pytest.approx(1.0 / 61.0)
    assert by_id[1].semantic_contribution == 0.0
    assert by_id[2].fused_score == pytest.approx(1.0 / 61.0)
    assert by_id[2].keyword_contribution == 0.0


def test_channel_weights_change_contribution() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion(
        k=60,
        keyword_weight=2.0,
        semantic_weight=1.0,
    ).fuse(
        keyword_results=[keyword(1)],
        semantic_results=[semantic(1)],
    )[0]

    assert result.keyword_contribution == pytest.approx(2.0 / 61.0)
    assert result.semantic_contribution == pytest.approx(1.0 / 61.0)
    assert result.fused_score == pytest.approx(3.0 / 61.0)


def test_rank_two_uses_rank_two_rrf_denominator() -> None:
    from src.retrieval.rank_fusion import RankFusion

    results = RankFusion(k=60).fuse(
        keyword_results=[keyword(1), keyword(2)],
    )

    assert results[0].entry_id == 1
    assert results[1].entry_id == 2
    assert results[1].keyword_rank == 2
    assert results[1].keyword_contribution == pytest.approx(1.0 / 62.0)


def test_results_are_sorted_by_fused_score_then_entry_id() -> None:
    from src.retrieval.rank_fusion import RankFusion

    results = RankFusion(k=60).fuse(
        keyword_results=[keyword(2), keyword(1)],
        semantic_results=[semantic(1), semantic(2)],
    )

    assert [result.entry_id for result in results] == [1, 2]


def test_duplicate_entry_in_one_channel_uses_first_rank() -> None:
    from src.retrieval.rank_fusion import RankFusion

    results = RankFusion(k=60).fuse(
        keyword_results=[
            keyword(1),
            keyword(1),
            keyword(2),
        ],
    )

    by_id = {result.entry_id: result for result in results}

    assert by_id[1].keyword_rank == 1
    assert by_id[1].keyword_contribution == pytest.approx(1.0 / 61.0)
    assert by_id[2].keyword_rank == 2


def test_top_k_limits_fused_results() -> None:
    from src.retrieval.rank_fusion import RankFusion

    results = RankFusion(k=60).fuse(
        keyword_results=[keyword(1), keyword(2), keyword(3)],
        top_k=2,
    )

    assert len(results) == 2


def test_invalid_configuration_is_rejected() -> None:
    from src.retrieval.rank_fusion import RankFusion

    with pytest.raises(ValueError):
        RankFusion(k=0)

    with pytest.raises(ValueError):
        RankFusion(k=-1)

    with pytest.raises(ValueError):
        RankFusion(keyword_weight=-1.0)

    with pytest.raises(ValueError):
        RankFusion(semantic_weight=-1.0)


def test_invalid_top_k_is_rejected() -> None:
    from src.retrieval.rank_fusion import RankFusion

    with pytest.raises(ValueError):
        RankFusion().fuse(
            keyword_results=[keyword(1)],
            top_k=0,
        )


def test_provenance_and_identity_are_preserved() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion().fuse(
        keyword_results=[keyword(42, "source-42")],
    )[0]

    assert result.entry_id == 42
    assert result.source_profile == "athena"
    assert result.origin_memory_id == "source-42"
    assert result.provenance == [
        {
            "source_profile": "athena",
            "origin_memory_id": "source-42",
        }
    ]


def test_fusion_does_not_depend_on_channel_specific_raw_scores() -> None:
    from src.retrieval.rank_fusion import RankFusion

    first = keyword(1)
    second = keyword(2)

    first = KeywordResult(
        entry_id=first.entry_id,
        source_profile=first.source_profile,
        origin_memory_id=first.origin_memory_id,
        score=-1000.0,
        provenance=first.provenance,
    )

    second = KeywordResult(
        entry_id=second.entry_id,
        source_profile=second.source_profile,
        origin_memory_id=second.origin_memory_id,
        score=-0.001,
        provenance=second.provenance,
    )

    results = RankFusion().fuse(
        keyword_results=[first, second],
    )

    assert results[0].entry_id == 1
    assert results[0].keyword_rank == 1
    assert results[1].entry_id == 2
    assert results[1].keyword_rank == 2


def entity(entry_id: int, origin: str | None = None):
    from src.retrieval.entity_search import EntityResult

    return EntityResult(
        entry_id=entry_id,
        source_profile="athena",
        origin_memory_id=origin or f"memory-{entry_id}",
        entity_score=1.0,
        provenance=[
            {
                "source_profile": "athena",
                "origin_memory_id": origin or f"memory-{entry_id}",
            }
        ],
    )


def test_entity_channel_uses_rank_one_rrf_score() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion(k=60).fuse(
        entity_results=[entity(1)],
    )[0]

    assert result.entry_id == 1
    assert result.entity_rank == 1
    assert result.entity_contribution == pytest.approx(1.0 / 61.0)
    assert result.fused_score == pytest.approx(1.0 / 61.0)

    assert result.keyword_rank is None
    assert result.semantic_rank is None
    assert result.graph_rank is None
    assert result.temporal_rank is None


def test_entity_channel_accumulates_with_existing_channels() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion(k=60).fuse(
        keyword_results=[keyword(1)],
        semantic_results=[semantic(1)],
        graph_results=[graph(1)],
        temporal_results=[temporal(1)],
        entity_results=[entity(1)],
    )[0]

    expected = 5.0 / 61.0

    assert result.keyword_rank == 1
    assert result.semantic_rank == 1
    assert result.graph_rank == 1
    assert result.temporal_rank == 1
    assert result.entity_rank == 1

    assert result.entity_contribution == pytest.approx(1.0 / 61.0)
    assert result.fused_score == pytest.approx(expected)


def test_entity_channel_weight_changes_contribution() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion(
        k=60,
        entity_weight=2.0,
    ).fuse(
        entity_results=[entity(1)],
    )[0]

    assert result.entity_contribution == pytest.approx(2.0 / 61.0)
    assert result.fused_score == pytest.approx(2.0 / 61.0)


def test_entity_channel_can_supply_canonical_identity() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion().fuse(
        entity_results=[entity(42, "entity-memory-42")],
    )[0]

    assert result.entry_id == 42
    assert result.source_profile == "athena"
    assert result.origin_memory_id == "entity-memory-42"
    assert result.provenance == [
        {
            "source_profile": "athena",
            "origin_memory_id": "entity-memory-42",
        }
    ]


def test_omitting_entity_channel_preserves_four_channel_score() -> None:
    from src.retrieval.rank_fusion import RankFusion

    result = RankFusion().fuse(
        keyword_results=[keyword(1)],
        semantic_results=[semantic(1)],
        graph_results=[graph(1)],
        temporal_results=[temporal(1)],
    )[0]

    assert result.fused_score == pytest.approx(4.0 / 61.0)
    assert result.entity_rank is None
    assert result.entity_contribution == 0.0


def test_entity_duplicate_entry_uses_first_rank() -> None:
    from src.retrieval.rank_fusion import RankFusion

    results = RankFusion().fuse(
        entity_results=[
            entity(1),
            entity(1),
            entity(2),
        ],
    )

    by_id = {result.entry_id: result for result in results}

    assert by_id[1].entity_rank == 1
    assert by_id[1].entity_contribution == pytest.approx(1.0 / 61.0)
    assert by_id[2].entity_rank == 2
    assert by_id[2].entity_contribution == pytest.approx(1.0 / 62.0)


def test_entity_weight_validation() -> None:
    from src.retrieval.rank_fusion import RankFusion

    with pytest.raises(ValueError):
        RankFusion(entity_weight=-1.0)

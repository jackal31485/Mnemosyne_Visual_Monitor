import numpy as np
import pytest

from src.domain.collective import CollectiveDAO
from src.domain.graph_aggregator import GraphAggregator
from src.retrieval.graph_search import GraphSearcher


def _make_dao(tmp_path):
    db_path = tmp_path / "collective.db"
    dao = CollectiveDAO(db_path=db_path)
    dao.ensure_schema()
    return dao


def _insert_promoted(dao, source_profile, memory_id):
    entry_id = dao.insert_collective_entry(
        source_profile=source_profile,
        origin_memory_id=memory_id,
    )
    dao.update_entry_promoted(entry_id)
    return entry_id


def _embed(dao, entry_id, vector):
    dao.update_entry_embedding(
        entry_id,
        np.asarray(vector, dtype=np.float32).tobytes(),
    )


def _make_searcher(dao, threshold=0.5):
    graph = GraphAggregator([dao], similarity_threshold=threshold)
    return GraphSearcher(dao, graph)


def test_graph_search_expands_one_hop(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    neighbor = _insert_promoted(dao, "athena", "neighbor")

    _embed(dao, seed, [1.0, 0.0])
    _embed(dao, neighbor, [0.99, 0.1])

    searcher = _make_searcher(dao)

    results = searcher.expand([seed])

    assert [result.entry_id for result in results] == [neighbor]
    assert results[0].source_profile == "athena"
    assert results[0].origin_memory_id == "neighbor"


def test_graph_search_preserves_duplicate_collective_entries(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    neighbor_a = _insert_promoted(dao, "athena", "same-memory")
    neighbor_b = _insert_promoted(dao, "athena", "same-memory")

    _embed(dao, seed, [1.0, 0.0])
    _embed(dao, neighbor_a, [0.99, 0.1])
    _embed(dao, neighbor_b, [0.98, 0.15])

    searcher = _make_searcher(dao)

    results = searcher.expand([seed])
    ids = [result.entry_id for result in results]

    assert neighbor_a in ids
    assert neighbor_b in ids
    assert len(ids) == 2


def test_graph_search_excludes_revoked_entries(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    neighbor = _insert_promoted(dao, "athena", "neighbor")

    dao.update_entry_revoked(neighbor, "test")

    _embed(dao, seed, [1.0, 0.0])
    _embed(dao, neighbor, [0.99, 0.1])

    searcher = _make_searcher(dao)

    assert searcher.expand([seed]) == []


def test_graph_search_excludes_unpromoted_entries(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    neighbor = dao.insert_collective_entry(
        source_profile="athena",
        origin_memory_id="neighbor",
    )

    _embed(dao, seed, [1.0, 0.0])
    _embed(dao, neighbor, [0.99, 0.1])

    searcher = _make_searcher(dao)

    assert searcher.expand([seed]) == []


def test_graph_search_profile_filter(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    athena_neighbor = _insert_promoted(dao, "athena", "a")
    odin_neighbor = _insert_promoted(dao, "odin", "o")

    _embed(dao, seed, [1.0, 0.0])
    _embed(dao, athena_neighbor, [0.99, 0.1])
    _embed(dao, odin_neighbor, [0.98, 0.15])

    searcher = _make_searcher(dao)

    results = searcher.expand([seed], profile="odin")

    assert [result.entry_id for result in results] == [odin_neighbor]


def test_graph_search_deduplicates_neighbors_across_seeds(tmp_path):
    dao = _make_dao(tmp_path)

    seed_a = _insert_promoted(dao, "athena", "seed-a")
    seed_b = _insert_promoted(dao, "athena", "seed-b")
    neighbor = _insert_promoted(dao, "athena", "neighbor")

    _embed(dao, seed_a, [1.0, 0.0])
    _embed(dao, seed_b, [0.99, 0.1])
    _embed(dao, neighbor, [0.98, 0.15])

    searcher = _make_searcher(dao)

    results = searcher.expand([seed_a, seed_b])

    assert [result.entry_id for result in results].count(neighbor) == 1


def test_graph_search_deterministic_order(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    first = _insert_promoted(dao, "athena", "first")
    second = _insert_promoted(dao, "athena", "second")

    _embed(dao, seed, [1.0, 0.0])
    _embed(dao, first, [0.9, 0.4358899])
    _embed(dao, second, [0.9, 0.4358899])

    searcher = _make_searcher(dao)

    results = searcher.expand([seed])

    assert [result.entry_id for result in results] == [first, second]


def test_graph_search_limit(tmp_path):
    dao = _make_dao(tmp_path)

    seed = _insert_promoted(dao, "athena", "seed")
    neighbors = [
        _insert_promoted(dao, "athena", f"neighbor-{i}")
        for i in range(3)
    ]

    _embed(dao, seed, [1.0, 0.0])

    for entry_id in neighbors:
        _embed(dao, entry_id, [0.99, 0.1])

    searcher = _make_searcher(dao)

    results = searcher.expand([seed], limit_per_seed=2)

    assert len(results) == 2
    assert [result.entry_id for result in results] == neighbors[:2]


def test_graph_search_rejects_invalid_limit(tmp_path):
    dao = _make_dao(tmp_path)
    searcher = _make_searcher(dao)

    with pytest.raises(ValueError):
        searcher.expand([], limit_per_seed=0)

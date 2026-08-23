"""
Unit tests for Phase 6.4 serialization contract.
"""

import os
import numpy as np
import pytest

from domain.collective import CollectiveDAO
from services.graph_service import GraphService

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def dao(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    dao = CollectiveDAO(db_path)
    dao.ensure_schema()
    yield dao
    dao.close()


def emb(v: np.ndarray) -> bytes:
    return v.astype(np.float32).tobytes()

# ---------------------------------------------------------------------------
# Tests – node/edge serialization
# ---------------------------------------------------------------------------

def promote_and_embed(dao, profile: str, memory_id: str, vec: np.ndarray):
    eid = dao.add_entry(profile, memory_id)
    dao.update_entry_promoted(eid)
    dao.update_entry_embedding(eid, emb(vec))
    return eid

# Node dictionary keys – all mandatory fields present.

def test_node_dict_keys(dao):
    promote_and_embed(dao, "alpha", "m1", np.array([0.5]))
    resp = GraphService([dao]).get_graph()
    assert len(resp["nodes"]) == 1
    node_keys = {
        "graph_id",
        "source_profile",
        "origin_memory_id",
        "lifecycle_state",
        "proposed_at",
        "validated_at",
        "validator_profile",
        "validation_score",
    }
    for n in resp["nodes"]:
        assert set(n.keys()) == node_keys

# Edge limit per source node and ordering.

def test_edge_limit_and_ordering(dao):
    # All entries from same profile with distinct embeddings.
    ids = []
    for label, vec in [("a", np.array([1.0, 0.0])),
                       ("b", np.array([0.9, 0.435])),
                       ("c", np.array([0.8, -0.6]))]:
        ids.append(promote_and_embed(dao, "alpha", label, vec))

    service = GraphService([dao])
    full = service.get_graph()
    # Node ordering deterministic.
    sorted_ids = sorted(n["graph_id"] for n in full["nodes"])
    assert [n["graph_id"] for n in full["nodes"]] == sorted_ids
    # For the node corresponding to "alpha:a", edges should be sorted by similarity desc.
    a_edges = full["edges"]["alpha:a"]
    if len(a_edges) >= 2:
        assert a_edges[0]["similarity_score"] > a_edges[1]["similarity_score"]

    limit_resp = service.get_graph(edge_limit=1)
    for lst in limit_resp["edges"].values():
        assert len(lst) <= 1

# Negative limit raises ValueError.

def test_negative_edge_limit(dao):
    promote_and_embed(dao, "alpha", "x", np.array([0.5]))
    svc = GraphService([dao])
    with pytest.raises(ValueError):
        svc.get_graph(edge_limit=-3)

# Source profile filtering – returns only matching nodes and edges.

def test_source_profile_filter(dao):
    promote_and_embed(dao, "alpha", "x", np.array([1.0]))
    promote_and_embed(dao, "beta",  "y", np.array([1.0]))

    svc = GraphService([dao])
    resp_alpha = svc.get_graph(source_profile="alpha")
    assert len(resp_alpha["nodes"]) == 1 and resp_alpha["nodes"][0]["graph_id"].startswith("alpha:")
    # No cross edges.
    for lst in resp_alpha["edges"].values():
        for e in lst:
            assert not e["target_id"].startswith("beta:")

# All profiles present when no filter applied.

def test_all_profiles_included(dao):
    promote_and_embed(dao, "alpha", "x", np.array([1.0]))
    promote_and_embed(dao, "beta",  "y", np.array([1.0]))

    svc = GraphService([dao])
    resp = svc.get_graph()
    assert len(resp["nodes"]) == 2
    for lst in resp["edges"].values():
        # Each source node can have at most one edge because embeddings are identical.
        assert len(lst) <= 1

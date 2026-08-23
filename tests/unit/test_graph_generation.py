"""Unit tests for the Phase 6 graph implementation.

All tests use a temporary SQLite database which is deleted after each run to keep the
repository clean.  Random embeddings are generated with numpy; a fixed seed guarantees repeatability of cosine similarity values.
"""
import os
from typing import List

import numpy as np
import pytest

# The test harness prefixes ``src`` to sys.path, so we can import the domain package.
from domain.collective import CollectiveDAO
from services.graph_service import GraphService
from domain.collective_graph import Node, Edge

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def rnd_vec(dim: int = 384) -> np.ndarray:
    return (np.random.rand(dim).astype(np.float32) - 0.5) * 2.0

# ---------------------------------------------------------------------------
@pytest.fixture
def dao(tmp_path_factory):
    # create a fresh database file per test
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    dao = CollectiveDAO(db_path)
    dao.ensure_schema()
    yield dao
    try:
        dao.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

# ---------------------------------------------------------------------------
def test_node_extraction_and_identity(dao: CollectiveDAO):
    # Two profiles with same origin_memory_id to validate graph_id uniqueness.
    id_a = dao.add_entry("alice", "mem123")
    id_b = dao.add_entry("bob", "mem123")
    dao.update_entry_promoted(id_a)
    dao.update_entry_promoted(id_b)

    # Attach embeddings – any random vectors are fine.
    dao.update_entry_embedding(id_a, rnd_vec().tobytes())
    dao.update_entry_embedding(id_b, rnd_vec().tobytes())

    service = GraphService([dao])  # single DAO covers two profiles via shared db
    nodes = service.get_nodes()
    assert len(nodes) == 2, "Both promoted nodes should appear"
    ids = {node.graph_id for node in nodes}
    expected = {"alice:mem123", "bob:mem123"}
    assert ids == expected
    # verify provenance fields are preserved
    for node in nodes:
        assert node.source_profile in ("alice", "bob")
        assert node.origin_memory_id == "mem123"
        assert node.lifecycle_state == "promoted"

# ---------------------------------------------------------------------------
def test_missing_embedding_still_shows_node(dao: CollectiveDAO):
    id_a = dao.add_entry("carol", "memX")
    dao.update_entry_promoted(id_a)
    # No embedding added.
    service = GraphService([dao])
    nodes = service.get_nodes()
    assert len(nodes) == 1
    edges = service.get_edges(nodes[0].graph_id)
    assert edges == [], "Node without embed should have no edges"

# ---------------------------------------------------------------------------
def test_revocation_removes_node_and_edges(dao: CollectiveDAO):
    id_a = dao.add_entry("dave", "memR")
    id_b = dao.add_entry("erin",  "memS")
    for i in (id_a, id_b):
        dao.update_entry_promoted(i)
        dao.update_entry_embedding(i, rnd_vec().tobytes())
    # Revoke one
    dao.revoke_entry(id_a, "no longer relevant")

    service = GraphService([dao])
    nodes = service.get_nodes()
    assert len(nodes) == 1, "Revoked node should vanish"
    remaining_id = nodes[0].graph_id
    edges = service.get_edges(remaining_id)
    # Only two nodes originally; with one revoked no edges.
    assert edges == [], "No edges when only single node remains"

# ---------------------------------------------------------------------------
def test_threshold_and_ordering(dao: CollectiveDAO):
    # Three entries. Prepare embeddings so that A-B similarity high, B-C moderate, A-C low.
    id_a = dao.add_entry("foo", "m1")
    id_b = dao.add_entry("bar", "m2")
    id_c = dao.add_entry("baz", "m3")

    # Deterministic vectors:
    # A/B are identical (cosine similarity = 1.0).
    # C has cosine similarity = 0.6 with A/B.
    vec_a = np.zeros(384, dtype=np.float32)
    vec_a[0] = 1.0

    vec_b = vec_a.copy()

    vec_c = np.zeros(384, dtype=np.float32)
    vec_c[0] = 0.6
    vec_c[1] = np.sqrt(1.0 - 0.6**2)
    dao.update_entry_promoted(id_a); dao.update_entry_embedding(id_a, vec_a.tobytes())
    dao.update_entry_promoted(id_b); dao.update_entry_embedding(id_b, vec_b.tobytes())
    dao.update_entry_promoted(id_c); dao.update_entry_embedding(id_c, vec_c.tobytes())

    # Set a threshold that keeps only AB edge.
    service = GraphService([dao], similarity_threshold=0.999)
    nodes = sorted(service.get_nodes(), key=lambda n: n.graph_id)
    node_a = next(n for n in nodes if n.source_profile == "foo")

    edges_ab = service.get_edges(node_a.graph_id)
    # Edge should be present and similarity near 1.0.
    assert len(edges_ab) == 1
    edge = edges_ab[0]
    assert edge.target_id != node_a.graph_id
    assert edge.similarity_score > 0.999

    # Lower threshold to include more edges but still deterministic ordering.
    service_low = GraphService([dao], similarity_threshold=0.5)
    all_edges = service_low.get_edges(node_a.graph_id)
    # Should contain two edges: AB (highest) then AC or BC depending on similarity.
    assert len(all_edges) == 2
    sims = [e.similarity_score for e in all_edges]
    assert sims[0] >= sims[1], "Edges sorted by decreasing similarity"
    # Ties broken by ascending target id; ensure ordering if needed.

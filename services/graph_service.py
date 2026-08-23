"""
Service layer exposing a minimal API for consumers.

The :class:`GraphService` is intentionally light‑weight – it forwards to an internal ``GraphAggregator``. All heavy lifting (node loading, edge generation, threshold filtering) happens inside the aggregator.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

# Local imports from domain package (test harness prepends ``src`` to sys.path)
try:
    from domain.collective import CollectiveDAO
except Exception:  # pragma: no cover – defensive fallback
    raise ImportError("CollectiveDAO not found in domain package")
from domain.graph_aggregator import GraphAggregator
from domain.collective_graph import Node, Edge

log = logging.getLogger(__name__)

class GraphService:
    """Convenient façade used by UI layers.

    Parameters are inherited from :class:`~domain.graph_aggregator.GraphAggregator` – a list of DAOs and an optional similarity threshold.
    """

    def __init__(self, daos: Iterable[CollectiveDAO], similarity_threshold: float = 0.75):
        self._agg = GraphAggregator(daos, similarity_threshold)

    # ----------------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------------
    def get_nodes(self) -> list[Node]:
        """Return all graph nodes in deterministic order.

        Nodes are sorted by their ``graph_id`` to guarantee repeatable output across runs.
        """
        return sorted(self._agg.nodes, key=lambda n: n.graph_id)

    def get_edges(self, source_graph_id: str, limit: int | None = None) -> list[Edge]:
        """Return the adjacency list for a single node.

        ``limit`` restricts the number of returned edges.  If omitted all qualifying
        edges are returned, sorted by similarity and target ID as described in Phase 6.3.
        """
        return self._agg.get_edges(source_graph_id, limit)

    # ----------------------------------------------------------------------------
    # Serialization helpers (private, exposed via ``get_graph``).
    # ----------------------------------------------------------------------------
    def _to_node_dict(self, node: Node) -> dict:
        return {
            "graph_id": node.graph_id,
            "source_profile": node.source_profile,
            "origin_memory_id": node.origin_memory_id,
            "lifecycle_state": node.lifecycle_state,
            "proposed_at": node.proposed_at,
            "validated_at": node.validated_at,
            "validator_profile": node.validator_profile,
            "validation_score": node.validation_score,
        }

    def _to_edge_dict(self, edge: Edge) -> dict:
        return {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "similarity_score": edge.similarity_score,
            "relationship_type": edge.relationship_type,
        }

    def get_graph(self, source_profile: str | None = None, edge_limit: int | None = None) -> dict:
        if edge_limit is not None:
            if not isinstance(edge_limit, int):
                raise ValueError("edge_limit must be an integer or None")
            if edge_limit < 0:
                raise ValueError("edge_limit cannot be negative")

        all_nodes = self.get_nodes()
        filtered_nodes = [n for n in all_nodes if source_profile is None or n.source_profile == source_profile]
        node_map = {n.graph_id: n for n in filtered_nodes}
        serialized_nodes = [self._to_node_dict(n) for n in filtered_nodes]
        adjacency: dict[str, list[dict]] = {}
        for src in filtered_nodes:
            raw_edges = self.get_edges(src.graph_id)
            valid_edges = [e for e in raw_edges if e.source_id in node_map and e.target_id in node_map]
            if edge_limit is not None:
                valid_edges = valid_edges[:edge_limit]
            adjacency[src.graph_id] = [self._to_edge_dict(e) for e in valid_edges]
        return {"nodes": serialized_nodes, "edges": adjacency}

    def rebuild(self) -> None:
        """Refresh the internal state from the DAOs.

        This is a cheap operation – only the DAO tables are re‑queried and embeddings
        re‑loaded.  Consumers may call this after bulk changes such as promotion or
        revocation to see up‑to‑date results without restarting the process.
        """
        self._agg.refresh()

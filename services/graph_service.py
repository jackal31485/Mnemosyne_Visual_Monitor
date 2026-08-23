"""Service layer exposing a minimal API for consumers.

The :class:`GraphService` is intentionally light‑weight – it forwards to an internal ``GraphAggregator``.  All heavy lifting (node loading, edge generation, threshold filtering) happens inside the aggregator.
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

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
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

    def rebuild(self) -> None:
        """Refresh the internal state from the DAOs.

        This is a cheap operation – only the DAO tables are re‑queried and embeddings
        re‑loaded.  Consumers may call this after bulk changes such as promotion or
        revocation to see up‑to‑date results without restarting the process.
        """
        self._agg.refresh()

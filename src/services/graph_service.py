"""Simple wrapper around :class:`~domain.graph_aggregator.GraphAggregator` exposing a minimal API used by the test‑suite.

The original Phase 6 repo exposed *services.graph_service*; it was inadvertently omitted.  The tests only require three operations:

```
service = GraphService([dao])
nodes          # list of :class:`Node`
edges(node_id)   # list of :class:`Edge`
```

The implementation below delegates to :class:`GraphAggregator` – it already implements ``refresh()``, ``nodes`` property, and ``get_edges()``.  We keep the behaviour deterministic and leave isolation logic unchanged.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from ..domain.graph_aggregator import GraphAggregator, Node, Edge
from ..domain.collective import CollectiveDAO


class GraphService:
    """Public façade for graph queries.

    Parameters are forwarded straight to :class:`GraphAggregator` so that the rest of
    the codebase remains untouched.  Clients construct a single instance per test
    run – the aggregator re‑refreshes on creation and never mutates afterwards.
    """

    def __init__(self, daos: Iterable[CollectiveDAO], similarity_threshold: float = 0.75):
        self._agg = GraphAggregator(daos, similarity_threshold)

    # ---------------------------------------------------------------------
    # Node API – mirrors the original test expectations.
    # ---------------------------------------------------------------------
    @property
    def nodes(self) -> List[Node]:  # pragma: no cover - thin proxy
        return self._agg.nodes

    def get_nodes(self) -> List[Node]:  # pragma: no cover - alias for consistency with tests
        return self._agg.nodes

    # ---------------------------------------------------------------------
    # Edge API – directly forwards to the aggregator.
    # ---------------------------------------------------------------------
    def get_edges(self, source_graph_id: str, limit: Optional[int] = None) -> List[Edge]:  # pragma: no cover - thin proxy
        return self._agg.get_edges(source_graph_id, limit)

    # ``edges`` method name for backward compatibility with older tests.
    def edges(self, source_graph_id: str, limit: Optional[int] = None) -> List[Edge]:  # pragma: no cover
        return self.get_edges(source_graph_id, limit)

# End of file

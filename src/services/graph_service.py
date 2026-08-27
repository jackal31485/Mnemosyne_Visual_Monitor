"""Public service façade for the Phase 6 collective graph."""

from __future__ import annotations

from typing import Iterable, Optional

from domain.collective import CollectiveDAO
from domain.graph_aggregator import GraphAggregator


class GraphService:
    """Build and serialize the read-only collective graph."""

    def __init__(
        self,
        daos: Iterable[CollectiveDAO],
        similarity_threshold: float = 0.75,
    ):
        self._agg = GraphAggregator(daos, similarity_threshold)

    def get_graph(
        self,
        source_profile: Optional[str] = None,
        edge_limit: Optional[int] = None,
    ) -> dict:
        """Return the public graph contract without exposing embeddings."""

        if edge_limit is not None and edge_limit < 0:
            raise ValueError("edge_limit must be >= 0")

        nodes = self._agg.nodes

        if source_profile is not None:
            nodes = [
                node
                for node in nodes
                if node.source_profile == source_profile
            ]

        node_ids = {node.graph_id for node in nodes}

        edges: dict[str, list[dict]] = {}

        for node in nodes:
            node_edges = self._agg.get_edges(node.graph_id, edge_limit)

            filtered_edges = [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "similarity_score": edge.similarity_score,
                    "relationship_type": "related",
                }
                for edge in node_edges
                if edge.target_id in node_ids
            ]

            edges[node.graph_id] = filtered_edges

        serialized_nodes = [
            {
                "graph_id": node.graph_id,
                "source_profile": node.source_profile,
                "origin_memory_id": node.origin_memory_id,
                "lifecycle_state": node.lifecycle_state,
                "proposed_at": node.proposed_at,
                "validated_at": node.validated_at,
                "validator_profile": node.validator_profile,
                "validation_score": node.validation_score,
            }
            for node in nodes
        ]

        return {
            "nodes": serialized_nodes,
            "edges": edges,
        }

    @property
    def nodes(self):
        return self._agg.nodes

    def get_nodes(self):
        return self._agg.nodes

    def get_edges(self, source_graph_id: str, limit: Optional[int] = None):
        return self._agg.get_edges(source_graph_id, limit)

    def edges(self, source_graph_id: str, limit: Optional[int] = None):
        return self.get_edges(source_graph_id, limit)

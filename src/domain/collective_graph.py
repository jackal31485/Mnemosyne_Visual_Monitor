"""Domain DTOs for graph nodes and edges used in Phase 6.3."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Node:
    """Represents a promoted, non‑revoked collective memory on the graph.

    ``graph_id`` is a unique identifier across profiles and is treated as an opaque token by all callers.
    All provenance information is included but never raw private content.  The fields
    come directly from :class:`CollectiveContract` plus any optional validation metadata.
    """
    graph_id: str
    source_profile: str
    origin_memory_id: str
    lifecycle_state: str
    proposed_at: Optional[str] = None
    validated_at: Optional[str] = None
    validator_profile: Optional[str] = None
    validation_score: Optional[float] = None

@dataclass(frozen=True)
class Edge:
    """Undirected similarity edge between two graph nodes.

    The source and target IDs are stored in deterministic order (lexicographic) but the
    caller is allowed to request edges from a specific node; see :mod:`graph_aggregator` for
    canonicalization rules.  ``similarity_score`` is a cosine similarity in [‑1, 1].
    """
    source_id: str
    target_id: str
    similarity_score: float
    relationship_type: str = "related"

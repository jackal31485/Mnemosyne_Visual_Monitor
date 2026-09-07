"""Graph construction logic for Phase 6.3.

The aggregator consumes a list of :class:`~domain.collective.CollectiveDAO` instances and pulls all promoted, non‑revoked entries.
It exposes ``refresh`` to re‑load data so that changes such as revocation or new promotion are reflected on subsequent queries without restarting the process.

Only a similarity threshold policy is implemented; the :class:`GraphService` wrapper can expose Top‑K on demand in future phases if required.
"""
import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
import numpy as np

# Local imports – DAO lives under ``src/domain``
try:
    from .collective import CollectiveDAO
except Exception:  # pragma: no cover – defensive import fallback
    raise ImportError("CollectiveDAO is required for graph aggregation")

from .collective_graph import Node, Edge

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _fetch_embedding(dao: CollectiveDAO, entry_id: int) -> np.ndarray | None:
    """Return a normalised float32 vector for *entry_id*.

    If the column is ``NULL`` or malformed it returns ``None`` and logs a warning.
    """
    try:
        result = dao.conn.execute(
            "SELECT embedding FROM collective_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not result or result["embedding"] is None:
            return None
        blob: bytes | memoryview = result["embedding"]
        vec = np.frombuffer(blob, dtype=np.float32).copy()
    except Exception as exc:  # pragma: no cover – defensive
        log.debug("Failed to read embedding for id %r: %s", entry_id, exc)
        return None
    if vec.size == 0:
        return None
    norm = np.linalg.norm(vec)
    if norm == 0.0:
        return None
    return vec / norm

# ---------------------------------------------------------------------------
class GraphAggregator:
    """Build an in‑memory semantic graph from promoted entries.

    Args:
        daos: Iterable of DAO instances – one per profile.
        similarity_threshold: Minimum cosine similarity for an edge to be kept.
    """

    def __init__(self, daos: Iterable[CollectiveDAO], similarity_threshold: float = 0.75):
        self.daos = list(daos)
        self.threshold = similarity_threshold
        # Internal state – populated on :meth:`refresh`.
        self._nodes_by_graph: Dict[str, Node] | None = None
        self._embeddings_by_entry: Dict[int, np.ndarray] | None = None
        self._entry_to_graph: Dict[int, str] | None = None
        self.refresh()

    def refresh(self) -> None:
        nodes: List[Node] = []
        embeddings: Dict[int, np.ndarray] = {}
        entry_map: Dict[int, str] = {}
        for dao in self.daos:
            try:
                promoted_ids = dao.list_promoted()
            except Exception as exc:  # pragma: no cover – defensive
                log.warning("DAO list_promoted failed: %s", exc)
                continue
            for pid in promoted_ids:
                state_tuple = dao.get_lifecycle_state(pid)  # (validated_at, is_revoked,...)
                if not state_tuple or state_tuple[1]:
                    # Revoked – skip entirely.
                    continue
                record = dao.get_by_id(pid)
                if not record:
                    log.warning("Missing entry id %r from DAO", pid)
                    continue
                _, src_prof, orig_mem, prop_at, val_at, val_score, val_user, *_ = record
                graph_id = f"{src_prof}:{orig_mem}"
                node = Node(
                    graph_id=graph_id,
                    source_profile=src_prof,
                    origin_memory_id=orig_mem,
                    lifecycle_state="promoted",
                    proposed_at=prop_at,
                    validated_at=val_at,
                    validator_profile=val_user,
                    validation_score=val_score,
                )
                nodes.append(node)
                entry_map[pid] = graph_id
                emb = _fetch_embedding(dao, pid)
                if emb is not None:
                    embeddings[pid] = emb
        self._nodes_by_graph = {node.graph_id: node for node in nodes}
        self._embeddings_by_entry = embeddings
        self._entry_to_graph = entry_map
        log.info("GraphAggregator refreshed – %d nodes, %d embeddings", len(nodes), len(embeddings))

    @property
    def nodes(self) -> List[Node]:
        return list(self._nodes_by_graph.values()) if self._nodes_by_graph else []

    @property
    def graph_ids(self) -> List[str]:
        return sorted(self._nodes_by_graph.keys()) if self._nodes_by_graph else []

    def get_neighbor_entries(
        self,
        entry_id: int,
        limit: Optional[int] = None,
    ) -> List[tuple[int, float]]:
        """Return qualifying graph neighbors using collective entry IDs.

        This retrieval-facing API deliberately preserves collective entry
        identity rather than converting through the presentation-oriented
        ``graph_id`` contract.

        Results are sorted by descending cosine similarity and then
        ascending collective entry ID.
        """
        try:
            entry_id = int(entry_id)
        except (TypeError, ValueError):
            raise ValueError("entry_id must be an integer")

        if limit is not None:
            if (
                not isinstance(limit, int)
                or isinstance(limit, bool)
                or limit < 1
            ):
                raise ValueError("limit must be a positive integer")

        source_embedding = self._embeddings_by_entry.get(entry_id)

        if source_embedding is None:
            return []

        results: List[tuple[int, float]] = []

        for target_entry_id, target_embedding in self._embeddings_by_entry.items():
            if target_entry_id == entry_id:
                continue

            similarity = float(np.dot(source_embedding, target_embedding))

            if similarity < self.threshold:
                continue

            results.append(
                (int(target_entry_id), similarity)
            )

        results.sort(key=lambda item: (-item[1], item[0]))

        if limit is not None:
            return results[:limit]

        return results

    def get_edges(self, source_graph_id: str, limit: Optional[int] = None) -> List[Edge]:
        """Return all qualifying edges for *source_graph_id*.

        Edges are sorted by
          1. descending similarity_score
          2. ascending target graph_id (tie breaker)

        If the source node has no embedding, an empty list is returned.
        """
        if not self._nodes_by_graph or source_graph_id not in self._nodes_by_graph:
            return []
        # find entry id for this graph id – reverse mapping via _entry_to_graph
        src_entry = None
        for eid, gid in self._entry_to_graph.items():
            if gid == source_graph_id:
                src_entry = eid
                break
        if src_entry is None or src_entry not in self._embeddings_by_entry:
            return []
        src_vec = self._embeddings_by_entry[src_entry]
        edges: List[Edge] = []
        for oid, tgt_vec in self._embeddings_by_entry.items():
            if oid == src_entry:
                continue
            sim = float(np.dot(src_vec, tgt_vec))
            if sim < self.threshold:
                continue
            # Determine target graph_id via entry map
            tgt_gid = self._entry_to_graph[oid]
            edge = Edge(source_id=source_graph_id, target_id=tgt_gid, similarity_score=sim)
            edges.append(edge)
        # Sort according to spec
        edges.sort(key=lambda e: (-e.similarity_score, e.target_id))
        if limit is not None:
            return edges[:limit]
        return edges

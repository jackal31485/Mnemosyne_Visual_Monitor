"""Governed entity-aware graph projection for Phase 10G.

This module projects already-authorized collective memories, resolved entities,
and governed relationships into a read-only graph representation.

The projection is derived data only:
- it never modifies source memories or collective lifecycle state;
- it never creates or modifies canonical entities;
- it never stores raw memory content;
- it preserves qualified profile identity and provenance references;
- it keeps explicit and inferred relationships distinct.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .collective import CollectiveDAO
from .entities import EntityDAO
from .entity_mentions import EntityMentionDAO
from .entity_resolutions import EntityResolutionDAO
from .relationships import RelationshipDAO


@dataclass(frozen=True)
class EntityGraphNode:
    """A node in the entity-aware graph projection."""

    node_id: str
    node_type: str
    lifecycle_state: str
    source_profile: str | None = None
    origin_memory_id: str | None = None
    entity_id: str | None = None
    canonical_name: str | None = None
    entity_type: str | None = None
    confidence: float | None = None
    mention_count: int = 0
    source_profiles: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityGraphEdge:
    """A governed edge in the entity-aware graph projection."""

    source_id: str
    target_id: str
    edge_type: str
    confidence: float | None = None
    relationship_kind: str | None = None
    collective_entry_id: int | None = None
    relationship_id: str | None = None
    mention_text: str | None = None
    source_profile: str | None = None
    source_memory_id: str | None = None


class EntityGraphProjector:
    """Build a deterministic read-only entity-aware graph projection."""

    def __init__(
        self,
        collective_dao: CollectiveDAO,
        entity_dao: EntityDAO,
        mention_dao: EntityMentionDAO,
        resolution_dao: EntityResolutionDAO,
        relationship_dao: RelationshipDAO,
    ) -> None:
        self.collective_dao = collective_dao
        self.entity_dao = entity_dao
        self.mention_dao = mention_dao
        self.resolution_dao = resolution_dao
        self.relationship_dao = relationship_dao

    def build(self) -> tuple[list[EntityGraphNode], list[EntityGraphEdge]]:
        """Build the authorized graph projection deterministically."""

        nodes: dict[str, EntityGraphNode] = {}
        edges: dict[
            tuple[
                str,
                str,
                str,
                str | None,
                int | None,
                str | None,
            ],
            EntityGraphEdge,
        ] = {}

        authorized_entries: dict[int, dict[str, Any]] = {}

        for entry_id in self.collective_dao.list_promoted():
            lifecycle = self.collective_dao.get_lifecycle_state(entry_id)

            if not lifecycle or lifecycle[1]:
                continue

            record = self.collective_dao.get_by_id(entry_id)
            if not record:
                continue

            (
                _,
                source_profile,
                origin_memory_id,
                *_,
            ) = record

            entry_id = int(entry_id)

            # Collective entry ID is authoritative for graph identity.
            # This prevents two distinct collective entries with the same
            # qualified source profile + origin memory ID from collapsing.
            memory_node_id = f"memory:collective:{entry_id}"

            nodes[memory_node_id] = EntityGraphNode(
                node_id=memory_node_id,
                node_type="memory",
                lifecycle_state="promoted",
                source_profile=source_profile,
                origin_memory_id=origin_memory_id,
            )

            authorized_entries[entry_id] = {
                "source_profile": source_profile,
                "origin_memory_id": origin_memory_id,
                "node_id": memory_node_id,
            }

        active_entities = {
            entity["entity_id"]: entity
            for entity in self.entity_dao.list(status="active")
        }

        entity_mentions: dict[str, int] = {}
        entity_profiles: dict[str, set[str]] = {}

        for mention in self.mention_dao.list():
            entry_id = int(mention["collective_entry_id"])

            if entry_id not in authorized_entries:
                continue

            resolution = self.resolution_dao.get_for_mention(
                mention["mention_id"]
            )

            if not resolution:
                continue

            # Only governed identity decisions may connect a mention to
            # a canonical entity. New/unresolved/ambiguous/rejected mentions
            # remain outside the entity graph.
            if resolution["decision"] != "same_entity":
                continue

            entity_id = resolution["proposed_entity_id"]

            if not isinstance(entity_id, str):
                continue

            entity = active_entities.get(entity_id)
            if entity is None:
                continue

            entity_node_id = f"entity:{entity_id}"
            memory_node_id = authorized_entries[entry_id]["node_id"]

            entity_mentions[entity_id] = (
                entity_mentions.get(entity_id, 0) + 1
            )
            entity_profiles.setdefault(entity_id, set()).add(
                mention["source_profile"]
            )

            nodes[entity_node_id] = EntityGraphNode(
                node_id=entity_node_id,
                node_type="entity",
                lifecycle_state=entity["status"],
                entity_id=entity_id,
                canonical_name=entity["canonical_name"],
                entity_type=entity["entity_type"],
                confidence=entity["confidence"],
                mention_count=entity_mentions[entity_id],
                source_profiles=tuple(
                    sorted(entity_profiles[entity_id])
                ),
            )

            edge = EntityGraphEdge(
                source_id=memory_node_id,
                target_id=entity_node_id,
                edge_type="mentions",
                confidence=mention["confidence"],
                collective_entry_id=entry_id,
                mention_text=mention["mention_text"],
                source_profile=mention["source_profile"],
                source_memory_id=mention["source_memory_id"],
            )

            key = (
                edge.source_id,
                edge.target_id,
                edge.edge_type,
                edge.relationship_id,
                edge.collective_entry_id,
                edge.relationship_kind,
            )
            edges[key] = edge

        for relationship in self.relationship_dao.list(status="active"):
            subject_id = relationship["subject_entity_id"]
            object_id = relationship["object_entity_id"]

            if subject_id not in active_entities:
                continue

            if object_id not in active_entities:
                continue

            subject_node_id = f"entity:{subject_id}"
            object_node_id = f"entity:{object_id}"

            for entity_id, entity_node_id in (
                (subject_id, subject_node_id),
                (object_id, object_node_id),
            ):
                entity = active_entities[entity_id]

                nodes.setdefault(
                    entity_node_id,
                    EntityGraphNode(
                        node_id=entity_node_id,
                        node_type="entity",
                        lifecycle_state=entity["status"],
                        entity_id=entity_id,
                        canonical_name=entity["canonical_name"],
                        entity_type=entity["entity_type"],
                        confidence=entity["confidence"],
                        mention_count=entity_mentions.get(
                            entity_id,
                            0,
                        ),
                        source_profiles=tuple(
                            sorted(
                                entity_profiles.get(
                                    entity_id,
                                    set(),
                                )
                            )
                        ),
                    ),
                )

            edge = EntityGraphEdge(
                source_id=subject_node_id,
                target_id=object_node_id,
                edge_type=relationship["predicate"],
                confidence=relationship["confidence"],
                relationship_kind=relationship["relationship_kind"],
                relationship_id=relationship["relationship_id"],
            )

            key = (
                edge.source_id,
                edge.target_id,
                edge.edge_type,
                edge.relationship_id,
                edge.collective_entry_id,
                edge.relationship_kind,
            )
            edges[key] = edge

        sorted_nodes = sorted(
            nodes.values(),
            key=lambda node: (node.node_type, node.node_id),
        )

        sorted_edges = sorted(
            edges.values(),
            key=lambda edge: (
                edge.source_id,
                edge.target_id,
                edge.edge_type,
                edge.relationship_id or "",
                edge.collective_entry_id or 0,
                edge.relationship_kind or "",
            ),
        )

        return sorted_nodes, sorted_edges

    def as_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Serialize the projection without exposing memory content."""

        nodes, edges = self.build()

        return {
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "lifecycle_state": node.lifecycle_state,
                    "source_profile": node.source_profile,
                    "origin_memory_id": node.origin_memory_id,
                    "entity_id": node.entity_id,
                    "canonical_name": node.canonical_name,
                    "entity_type": node.entity_type,
                    "confidence": node.confidence,
                    "mention_count": node.mention_count,
                    "source_profiles": list(node.source_profiles),
                }
                for node in nodes
            ],
            "edges": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "edge_type": edge.edge_type,
                    "confidence": edge.confidence,
                    "relationship_kind": edge.relationship_kind,
                    "collective_entry_id": edge.collective_entry_id,
                    "relationship_id": edge.relationship_id,
                    "mention_text": edge.mention_text,
                    "source_profile": edge.source_profile,
                    "source_memory_id": edge.source_memory_id,
                }
                for edge in edges
            ],
        }

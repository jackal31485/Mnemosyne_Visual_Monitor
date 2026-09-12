"""Pydantic response schemas for the read-only graph API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EdgeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_id: str
    similarity_score: float
    relationship_type: str = "related"


class NodeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    source_profile: str
    origin_memory_id: str
    lifecycle_state: str
    proposed_at: str | None = None
    validated_at: str | None = None
    validator_profile: str | None = None
    validation_score: float | None = None


class GraphResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[NodeDTO]
    edges: dict[str, list[EdgeDTO]]


class ProfileDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    memory_count: int


class EntityGraphNodeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    source_profiles: list[str] = []


class EntityGraphEdgeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class EntityGraphResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[EntityGraphNodeDTO]
    edges: list[EntityGraphEdgeDTO]

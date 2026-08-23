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

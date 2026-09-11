"""Public read-only service façade for the Phase 10 entity graph."""

from __future__ import annotations


from domain.collective import CollectiveDAO
from domain.entities import EntityDAO
from domain.entity_graph import EntityGraphProjector
from domain.entity_mentions import EntityMentionDAO
from domain.entity_resolutions import EntityResolutionDAO
from domain.relationships import RelationshipDAO


class EntityGraphService:
    """Build and serialize the governed entity-aware graph."""

    def __init__(
        self,
        collective_dao: CollectiveDAO,
        entity_dao: EntityDAO,
        mention_dao: EntityMentionDAO,
        resolution_dao: EntityResolutionDAO,
        relationship_dao: RelationshipDAO,
    ) -> None:
        self._projector = EntityGraphProjector(
            collective_dao=collective_dao,
            entity_dao=entity_dao,
            mention_dao=mention_dao,
            resolution_dao=resolution_dao,
            relationship_dao=relationship_dao,
        )

    def get_graph(self) -> dict:
        """Return the governed entity graph without memory content."""
        return self._projector.as_dict()

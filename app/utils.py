from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain.collective import CollectiveDAO
from domain.entities import EntityDAO
from domain.entity_mentions import EntityMentionDAO
from domain.entity_resolutions import EntityResolutionDAO
from domain.relationships import RelationshipDAO
from services.entity_graph_service import EntityGraphService
from services.graph_service import GraphService


def build_graph_service() -> GraphService:
    """Construct the read-only graph service from the collective database.

    The visualization layer must only consume collective knowledge. Individual
    Hermes profile databases remain outside the visualization boundary.
    """
    collective_db = PROJECT_ROOT / "data" / "collective.db"

    dao = CollectiveDAO(collective_db)
    dao.ensure_schema()

    return GraphService(
        [dao],
        similarity_threshold=0.75,
    )


def build_entity_graph_service() -> EntityGraphService:
    """Construct the read-only entity graph service from the collective database.

    The entity-aware visualization layer must only consume governed collective
    knowledge. Individual Hermes profile databases remain outside the
    visualization boundary.
    """
    collective_db = PROJECT_ROOT / "data" / "collective.db"

    collective_dao = CollectiveDAO(collective_db)
    entity_dao = EntityDAO(collective_db)
    mention_dao = EntityMentionDAO(collective_db)
    resolution_dao = EntityResolutionDAO(collective_db)
    relationship_dao = RelationshipDAO(collective_db)

    collective_dao.ensure_schema()
    entity_dao.ensure_schema()
    mention_dao.ensure_schema()
    resolution_dao.ensure_schema()
    relationship_dao.ensure_schema()

    return EntityGraphService(
        collective_dao=collective_dao,
        entity_dao=entity_dao,
        mention_dao=mention_dao,
        resolution_dao=resolution_dao,
        relationship_dao=relationship_dao,
    )

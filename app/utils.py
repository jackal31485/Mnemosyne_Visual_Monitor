from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain.collective import CollectiveDAO
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

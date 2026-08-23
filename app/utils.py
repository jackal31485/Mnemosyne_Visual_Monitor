from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain.collective import CollectiveDAO
from services.graph_service import GraphService

from .config import get_profile_db_paths


def build_daos() -> Mapping[str, CollectiveDAO]:
    """Construct one CollectiveDAO for each configured Hermes profile.

    Database locations are supplied through the environment by
    app.config.get_profile_db_paths(). No database paths are hardcoded
    into the API layer.
    """
    return {
        profile: CollectiveDAO(db_path)
        for profile, db_path in get_profile_db_paths().items()
    }


def build_graph_service() -> GraphService:
    """Construct the read-only graph service from configured profile DAOs."""
    daos = build_daos()

    return GraphService(
        daos.values(),
        similarity_threshold=0.75,
    )

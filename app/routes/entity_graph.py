from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from services.entity_graph_service import EntityGraphService

from ..schemas import EntityGraphResponse
from ..utils import build_entity_graph_service


router = APIRouter()


def entity_graph_service_dep() -> EntityGraphService:
    return build_entity_graph_service()


@router.get(
    "/api/entity-graph",
    response_model=EntityGraphResponse,
)
def get_entity_graph(
    graph_service: EntityGraphService = Depends(entity_graph_service_dep),
) -> EntityGraphResponse:
    """Return the governed entity-aware graph projection."""
    return EntityGraphResponse(**graph_service.get_graph())

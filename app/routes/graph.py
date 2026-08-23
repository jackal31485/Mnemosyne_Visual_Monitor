from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from services.graph_service import GraphService

from ..schemas import GraphResponse
from ..utils import build_graph_service


router = APIRouter()


def graph_service_dep() -> GraphService:
    return build_graph_service()


@router.get("/api/graph", response_model=GraphResponse)
def get_graph(
    source_profile: Optional[str] = Query(
        None,
        description="Filter nodes to this profile",
    ),
    edge_limit: Optional[int] = Query(
        None,
        ge=0,
        description="Maximum edges per node",
    ),
    graph_service: GraphService = Depends(graph_service_dep),
) -> GraphResponse:
    try:
        graph = graph_service.get_graph(
            source_profile=source_profile,
            edge_limit=edge_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return GraphResponse(**graph)

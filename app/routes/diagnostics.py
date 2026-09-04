from fastapi import APIRouter
from ..routes.profiles import get_profiles
from ..utils import build_graph_service
from ..schemas import ProfileDTO

router = APIRouter()

# ------------------------------------------------------------------
# Diagnostics for profiles.
# ------------------------------------------------------------------
@router.get("/profiles/diag", description="Profile statistics for debugging")
def profiles_diag():
    profiles = get_profiles()
    total_profiles = len(profiles)
    total_memories = sum(p.memory_count for p in profiles)
    return {
        "total_profiles": total_profiles,
        "total_memories": total_memories,
        "profiles": [
            {"id": p.id, "name": p.name, "memory_count": p.memory_count}
            for p in profiles
        ],
    }

# ------------------------------------------------------------------
# Diagnostics for graph.
# ------------------------------------------------------------------
@router.get("/graph/diag", description="Graph statistics for debugging")
def graph_diag():
    service = build_graph_service()
    raw = service.get_graph()
    nodes = raw["nodes"]
    edges = raw["edges"]
    node_count = len(nodes)
    edge_count = sum(len(v) for v in edges.values())
    return {
        "node_count": node_count,
        "edge_count": edge_count,
    }

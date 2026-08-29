from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Existing project domain modules live under src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from app.routes.graph import router as graph_router
from app.routes.profiles import router as profiles_router
from app.routes.discovery import router as discovery_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Mnemosyne Visual Monitor – Read-Only Graph API"
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:12345",
            "http://localhost:12345",
        ],
        allow_methods=["GET"],
        allow_headers=[],
    )
    application.include_router(graph_router)
    application.include_router(profiles_router)
    application.include_router(discovery_router)
    return application


app = create_app()

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI

# Existing project domain modules live under src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from app.routes.graph import router as graph_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Mnemosyne Visual Monitor – Read-Only Graph API"
    )
    application.include_router(graph_router)
    return application


app = create_app()

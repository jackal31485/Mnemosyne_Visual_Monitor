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

from app.routes.admin import router as admin_router
from app.routes.graph import router as graph_router
from app.routes.profiles import router as profiles_router
from app.routes.discovery import router as discovery_router


def _register_router_directly(application: FastAPI, router) -> None:
    """
    Register an APIRouter's already-built route objects directly.

    This is intentionally used for the admin router because the project
    currently has a situation where FastAPI's include_router() is not
    producing the expected application routes.
    """
    for route in router.routes:
        if route not in application.router.routes:
            application.router.routes.append(route)


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
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
        ],
    )

    # Register admin routes directly.
    _register_router_directly(application, admin_router)

    # Existing application routers.
    application.include_router(graph_router)
    application.include_router(profiles_router)
    application.include_router(discovery_router)

    return application


app = create_app()

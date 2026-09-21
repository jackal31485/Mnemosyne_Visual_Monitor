"""FastAPI application for Mnemosyne Visual Monitor."""
from fastapi import FastAPI
from app.discovery_beacon import DiscoveryBeacon
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys
from pathlib import Path
import os

# Compute project roots.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Import routers.
from app.routes.admin import router as admin_router
from app.routes.entity_graph import router as entity_graph_router
from app.routes.graph import router as graph_router
from app.routes.profiles import router as profiles_router
from app.routes.discovery import router as discovery_router
from app.routes.browser import router as browser_router
from app.routes.diagnostics import router as diagnostics_router
from app.routes.memories import router as memories_router
from app.routes.timeline import router as timeline_router
from app.routes.search import router as search_router
from app.routes.temporal_history import router as temporal_history_router
from app.routes.temporal_visualization import router as temporal_visualization_router
from app.routes.mental_models import router as mental_models_router
from app.routes.transfer_learning import router as transfer_learning_router

# Helper for legacy admin route registration.
def _register_router_directly(application: FastAPI, router) -> None:
    """Register an APIRouter's already-built route objects directly."""
    for route in router.routes:
        if route not in application.router.routes:
            application.router.routes.append(route)

# Application entry point.
def create_app() -> FastAPI:
    application = FastAPI(
        title="Mnemosyne Visual Monitor – Browser and Collective API"
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:12345",
            "http://localhost:12345",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    # Mount static files for UI assets.
    application.mount("/static", StaticFiles(directory="ui"), name="static")

    # Register admin routes directly.
    _register_router_directly(application, admin_router)
    # Browser routes provide /browser and UI assets.
    _register_router_directly(application, browser_router)

    # Existing application routers.
    _register_router_directly(application, graph_router)
    _register_router_directly(application, entity_graph_router)
    _register_router_directly(application, profiles_router)
    _register_router_directly(application, discovery_router)
    

    # Diagnostics endpoints
    application.include_router(diagnostics_router)
    _register_router_directly(application, memories_router)
    _register_router_directly(application, timeline_router)
    _register_router_directly(application, temporal_history_router)
    _register_router_directly(application, temporal_visualization_router)
    _register_router_directly(application, mental_models_router)
    _register_router_directly(application, transfer_learning_router)
    application.include_router(search_router)

    return application

app = create_app()

# ---------------------------------------------------------------------------
# Minimal root endpoint for TestClient compatibility
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, str | None]:
    """Return a minimal operational liveness response."""
    return {
        "status": "ok",
        "service": "mnemosyne-visual-monitor",
        "version": os.getenv("MNEMOSYNE_VERSION"),
    }


@app.get("/")
def read_root() -> str:
    """Return the main browser page.

    The original repository served this via a separate route but tests expect a
    standalone ``/`` endpoint that returns the UI HTML. This lightweight
    function is sufficient for TestClient checks and does not alter the normal
    application behaviour.
    """
    import os

    ui_path = PROJECT_ROOT / "ui" / "browser.html"
    with open(str(ui_path), "r", encoding="utf-8") as fh:
        return fh.read()

# Self‑discoverable registration ------------------------------------
from app.discovery import DB_PATH
import sqlite3

_discovery_beacon = DiscoveryBeacon(api_port=8000)

def _register_self_discoverable() -> None:
    """Persist the local instance as a discoverable agent.
    On machines where multicast loopback is disabled there will be no outgoing
    packets for the listener to consume. The UI expects at least one record, so we insert the beacon's
    own data into the database during startup."""
    from datetime import datetime

    now_ts = int(datetime.utcnow().timestamp())
    # Determine the LAN-reachable address for this instance.
    # The discovery listener must never advertise 0.0.0.0 or localhost.
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("224.10.0.1", 34567))
        local_address = probe.getsockname()[0]
    except OSError:
        local_address = socket.gethostbyname(socket.gethostname())
    finally:
        probe.close()

    rec = (
        _discovery_beacon.client_id,
        _discovery_beacon.hostname,
        _discovery_beacon.version,
        local_address,
        _discovery_beacon.api_port,
        now_ts,
        now_ts,
    )
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO discovery_records
                (client_id, hostname, installed_version, address, api_port, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(client_id) DO UPDATE SET
                hostname=excluded.hostname,
                installed_version=excluded.installed_version,
                address=excluded.address,
                api_port=excluded.api_port,
                last_seen=excluded.last_seen
            """,
            rec,
        )

@app.on_event("startup")
def _start_discovery_beacon_and_register() -> None:
    _discovery_beacon.start()
    _register_self_discoverable()

@app.on_event("shutdown")
def _stop_discovery_beacon() -> None:
    _discovery_beacon.stop()

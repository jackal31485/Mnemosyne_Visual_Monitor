"""Discovery API endpoints.

This module provides two HTTP endpoints used by the Web UI:

* ``GET /api/discovery`` – returns currently persisted discovery records.
* ``POST /api/discovery/scan`` – triggers a bounded multicast scan that writes
  to the same SQLite database used by :class:`app.discovery.DiscoveryListener`.

The implementation intentionally keeps the logic minimal and re‑uses the core
multicast listener defined in :mod:`app.discovery`.  It does not persist state
outside the ``discovery.db`` file, so all discovered agents are available to
the UI via the simple GET endpoint after a scan has completed.
"""

from __future__ import annotations

import datetime as _dt
import time
import sqlite3
from pathlib import Path
from fastapi import APIRouter
from starlette.responses import JSONResponse

from ..discovery import (
    DiscoveryListener,
    DB_PATH as DISCOVERY_DB_PATH,
)

router = APIRouter()

def _load_records(db_path: Path):  # pragma: no cover – exercised indirectly
    """Return all rows from :pydata:`discovery_records` table as JSON‑serialisable dicts."""
    records: list[dict] = []
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute(
            "SELECT client_id, hostname, installed_version, first_seen, last_seen, state FROM discovery_records ORDER BY last_seen DESC"
        )
        for row in cursor.fetchall():
            records.append(
                {
                    "client_id": row[0],
                    "hostname": row[1],
                    "installed_version": row[2],
                    "first_seen": _dt.datetime.utcfromtimestamp(row[3]).isoformat() + "Z",
                    "last_seen": _dt.datetime.utcfromtimestamp(row[4]).isoformat() + "Z",
                    "state": row[5],
                }
            )
    return records

@router.get("/api/discovery", response_class=JSONResponse)
def get_discovered_agents() -> dict:
    """Return all agents currently stored in the discovery DB."""
    records = _load_records(DISCOVERY_DB_PATH)
    return {"agents": records}

@router.post("/api/discovery/scan", response_class=JSONResponse)
def post_discover_agents() -> dict:
    """Run a bounded multicast discovery scan and return newly persisted agents."""
    _SCAN_DURATION = 2.0
    listener = DiscoveryListener(shutdown_event=None, db_path=DISCOVERY_DB_PATH)
    try:
        listener.start()
        time.sleep(_SCAN_DURATION)
    finally:
        listener.stop()
    records = _load_records(DISCOVERY_DB_PATH)
    return {"agents": records, "duration_seconds": _SCAN_DURATION}

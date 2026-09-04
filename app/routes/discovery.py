"""LAN discovery and agent adoption API."""

from __future__ import annotations

import datetime as _dt
import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from ..discovery import (
    DB_PATH as DISCOVERY_DB_PATH,
    STALE_THRESHOLD_SECONDS,
)
from ..discovery_scan import scan_controller



router = APIRouter()


def _ensure_discovery_schema(conn):
    """Ensure discovery_records supports current discovery metadata."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS discovery_records (
            client_id TEXT PRIMARY KEY,
            hostname TEXT,
            installed_version TEXT,
            first_seen INTEGER,
            last_seen INTEGER,
            state TEXT NOT NULL DEFAULT 'DISCOVERED',
            address TEXT,
            api_port INTEGER
        )
    """)

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(discovery_records)"
        ).fetchall()
    }

    if "address" not in columns:
        conn.execute(
            "ALTER TABLE discovery_records ADD COLUMN address TEXT"
        )

    if "api_port" not in columns:
        conn.execute(
            "ALTER TABLE discovery_records ADD COLUMN api_port INTEGER"
        )

    conn.commit()


def _iso(timestamp):
    if timestamp is None:
        return None

    return _dt.datetime.fromtimestamp(
        timestamp,
        tz=_dt.timezone.utc,
    ).isoformat()


def _load_records(
    db_path: Path,
    include_stale: bool = False,
) -> list[dict]:

    records = []
    now = int(time.time())

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_discovery_schema(conn)

        rows = conn.execute(
            """
            SELECT
                client_id,
                hostname,
                installed_version,
                address,
                api_port,
                first_seen,
                last_seen,
                state
            FROM discovery_records
            ORDER BY last_seen DESC
            """
        ).fetchall()

        for row in rows:
            last_seen = row["last_seen"]
            stale = (
                last_seen is None
                or now - int(last_seen) > STALE_THRESHOLD_SECONDS
            )

            if stale and not include_stale and row["state"] != "ADOPTED":
                continue

            records.append(
                {
                    "client_id": row["client_id"],
                    "hostname": row["hostname"],
                    "installed_version": row["installed_version"],
                    "address": row["address"],
                    "api_port": row["api_port"],
                    "first_seen": _iso(row["first_seen"]),
                    "last_seen": _iso(row["last_seen"]),
                    "state": row["state"],
                    "stale": stale,
                }
            )

    return records


@router.get(
    "/api/discovery",
    response_class=JSONResponse,
)
def get_discovered_agents() -> dict:
    return {
        "agents": _load_records(
            DISCOVERY_DB_PATH,
            include_stale=False,
        ),
        "scanning": scan_controller.running,
    }


@router.get(
    "/api/discovery/all",
    response_class=JSONResponse,
)
def get_all_discovery_records() -> dict:
    return {
        "agents": _load_records(
            DISCOVERY_DB_PATH,
            include_stale=True,
        ),
        "scanning": scan_controller.running,
    }


@router.get(
    "/api/discovery/status",
    response_class=JSONResponse,
)
def get_discovery_status() -> dict:
    agents = _load_records(
        DISCOVERY_DB_PATH,
        include_stale=False,
    )

    adopted = [
        agent
        for agent in agents
        if agent["state"] == "ADOPTED"
    ]

    return {
        "running": scan_controller.running,
        "discovered": len(agents),
        "adopted": len(adopted),
    }


@router.post(
    "/api/discovery/scan/start",
    response_class=JSONResponse,
)
def start_discovery_scan() -> dict:
    started = scan_controller.start()

    return {
        "started": started,
        "scanning": scan_controller.running,
        "agents": _load_records(
            DISCOVERY_DB_PATH,
            include_stale=False,
        ),
    }


@router.post(
    "/api/discovery/scan/stop",
    response_class=JSONResponse,
)
def stop_discovery_scan() -> dict:
    stopped = scan_controller.stop()

    return {
        "stopped": stopped,
        "scanning": scan_controller.running,
        "agents": _load_records(
            DISCOVERY_DB_PATH,
            include_stale=False,
        ),
    }


@router.post(
    "/api/discovery/{client_id}/adopt",
    response_class=JSONResponse,
)
def adopt_discovered_agent(client_id: str) -> dict:

    with sqlite3.connect(
        str(DISCOVERY_DB_PATH)
    ) as conn:



        _ensure_discovery_schema(conn)
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT
                client_id,
                hostname,
                installed_version,
                address,
                api_port,
                first_seen,
                last_seen,
                state
            FROM discovery_records
            WHERE client_id = ?
            """,
            (client_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Discovery agent not found",
            )

        already_adopted = row["state"] == "ADOPTED"

        if not already_adopted:
            conn.execute(
                """
                UPDATE discovery_records
                SET state = 'ADOPTED'
                WHERE client_id = ?
                """,
                (client_id,),
            )

            conn.commit()

        return {
            "adopted": not already_adopted,
            "agent": {
                "client_id": row["client_id"],
                "hostname": row["hostname"],
                "installed_version": row[
                    "installed_version"
                ],
                "address": row["address"],
                "api_port": row["api_port"] or 8000,
                "first_seen": _iso(
                    row["first_seen"]
                ),
                "last_seen": _iso(
                    row["last_seen"]
                ),
                "state": "ADOPTED",
                "stale": False,
                "online": True,
            },
        }


@router.post(
    "/api/discovery/{client_id}/unadopt",
    response_class=JSONResponse,
)
def unadopt_discovered_agent(client_id: str) -> dict:

    with sqlite3.connect(
        str(DISCOVERY_DB_PATH)
    ) as conn:



        _ensure_discovery_schema(conn)
        row = conn.execute(
            """
            SELECT client_id
            FROM discovery_records
            WHERE client_id = ?
            """,
            (client_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Discovery agent not found",
            )

        conn.execute(
            """
            UPDATE discovery_records
            SET state = 'DISCOVERED'
            WHERE client_id = ?
            """,
            (client_id,),
        )

        conn.commit()

    return {
        "unadopted": True,
        "client_id": client_id,
    }

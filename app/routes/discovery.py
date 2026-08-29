"""LAN discovery and agent-management API."""

from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from ..discovery import DB_PATH as DISCOVERY_DB_PATH
from ..discovery_scan import scan_controller

router = APIRouter()


def _load_records(db_path: Path) -> list[dict]:
    records: list[dict] = []

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute(
            """
            SELECT
                client_id,
                hostname,
                installed_version,
                first_seen,
                last_seen,
                state
            FROM discovery_records
            ORDER BY last_seen DESC
            """
        )

        for row in cursor.fetchall():
            records.append(
                {
                    "client_id": row[0],
                    "hostname": row[1],
                    "installed_version": row[2],
                    "first_seen": (
                        _dt.datetime.fromtimestamp(
                            row[3], tz=_dt.timezone.utc
                        ).isoformat()
                    ),
                    "last_seen": (
                        _dt.datetime.fromtimestamp(
                            row[4], tz=_dt.timezone.utc
                        ).isoformat()
                    ),
                    "state": row[5],
                }
            )

    return records


@router.get("/api/discovery", response_class=JSONResponse)
def get_discovered_agents() -> dict:
    return {
        "agents": _load_records(DISCOVERY_DB_PATH),
        "scanning": scan_controller.running,
    }


@router.get("/api/discovery/status", response_class=JSONResponse)
def get_discovery_status() -> dict:
    return scan_controller.status()


@router.post("/api/discovery/scan/start", response_class=JSONResponse)
def start_discovery_scan() -> dict:
    started = scan_controller.start()

    return {
        "started": started,
        "scanning": scan_controller.running,
        "agents": _load_records(DISCOVERY_DB_PATH),
    }


@router.post("/api/discovery/scan/stop", response_class=JSONResponse)
def stop_discovery_scan() -> dict:
    stopped = scan_controller.stop()

    return {
        "stopped": stopped,
        "scanning": scan_controller.running,
        "agents": _load_records(DISCOVERY_DB_PATH),
    }


@router.post("/api/discovery/{client_id}/adopt", response_class=JSONResponse)
def adopt_discovered_agent(client_id: str) -> dict:
    """Mark a discovered agent as adopted.

    Adoption only changes the discovery lifecycle state. It does not create
    profiles, copy memories, or otherwise cross the discovery/profile boundary.
    """

    with sqlite3.connect(str(DISCOVERY_DB_PATH)) as conn:
        cursor = conn.execute(
            """
            SELECT
                client_id,
                hostname,
                installed_version,
                first_seen,
                last_seen,
                state
            FROM discovery_records
            WHERE client_id=?
            """,
            (client_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Discovery agent not found")

        adopted = row[5] != "ADOPTED"

        if adopted:
            conn.execute(
                """
                UPDATE discovery_records
                SET state='ADOPTED'
                WHERE client_id=?
                """,
                (client_id,),
            )
            conn.commit()

        state = "ADOPTED"

        agent = {
            "client_id": row[0],
            "hostname": row[1],
            "installed_version": row[2],
            "first_seen": (
                _dt.datetime.fromtimestamp(
                    row[3], tz=_dt.timezone.utc
                ).isoformat()
            ),
            "last_seen": (
                _dt.datetime.fromtimestamp(
                    row[4], tz=_dt.timezone.utc
                ).isoformat()
            ),
            "state": state,
        }

    return {
        "adopted": adopted,
        "agent": agent,
    }

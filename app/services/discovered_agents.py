from __future__ import annotations

import sqlite3

from src.domain.agent_rebuild import AgentEndpoint
from app.discovery import DB_PATH


def get_discovered_agents() -> list[AgentEndpoint]:
    """
    Return adopted, currently-online agents as rebuild endpoints.

    Discovery is the authority for endpoint information.
    """

    agents = []

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                client_id,
                hostname,
                address,
                api_port,
                last_seen,
                state
            FROM discovery_records
            WHERE state = 'ADOPTED'
            ORDER BY hostname
            """
        ).fetchall()

        for row in rows:
            address = row["address"]
            api_port = row["api_port"] or 8000
            last_seen = row["last_seen"]

            if not address:
                continue

            agents.append(
                AgentEndpoint(
                    agent_id=row["client_id"],
                    hostname=row["hostname"] or row["client_id"],
                    base_url=(
                        f"http://{address}:{api_port}"
                    ),
                )
            )

    return agents

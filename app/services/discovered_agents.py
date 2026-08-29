from __future__ import annotations

from src.domain.agent_rebuild import AgentEndpoint


def get_discovered_agents() -> list[AgentEndpoint]:
    """
    Adapt the existing Phase 6.5C discovery records into rebuild endpoints.

    Replace only the database query below with the existing discovery
    DAO/query already used by app/routes/discovery.py if the column names
    differ.
    """

    from app.db.discovery import get_discovered_clients

    rows = get_discovered_clients()

    agents: list[AgentEndpoint] = []

    for row in rows:
        agent_id = row["client_id"]
        hostname = row["hostname"]

        # Discovery must advertise the HTTP API address/port.
        address = row.get("address") or row.get("ip_address")

        if not address:
            continue

        port = row.get("port", 8000)

        agents.append(
            AgentEndpoint(
                agent_id=agent_id,
                hostname=hostname,
                base_url=f"http://{address}:{port}",
            )
        )

    return agents
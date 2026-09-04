from __future__ import annotations

from src.domain.agent_rebuild import AgentMemoryClient
from src.domain.live_memory_gateway import LiveMemoryGateway
from src.domain.memory_gateway import MemoryGateway
from app.services.discovered_agents import get_discovered_agents


class DistributedMemoryGateway:
    """Route source-memory reads to the local or discovered agent.

    Local profiles such as ``athena`` are read through the local
    LiveMemoryGateway.

    Distributed profiles use the form::

        <agent_id>:<profile>

    and are resolved through LAN discovery before being fetched from
    the adopted agent.
    """

    def __init__(self) -> None:
        self._local = LiveMemoryGateway()

    def get_memory(self, profile: str, memory_id: str) -> str:
        profile = str(profile)
        memory_id = str(memory_id)

        if ":" not in profile:
            return self._local.get_memory(profile, memory_id)

        agent_id, remote_profile = profile.split(":", 1)

        if not agent_id or not remote_profile:
            raise KeyError(
                f"Invalid distributed source profile: {profile}"
            )

        for endpoint in get_discovered_agents():
            if endpoint.agent_id != agent_id:
                continue

            client = AgentMemoryClient(endpoint)
            return client.get_memory(remote_profile, memory_id)

        raise KeyError(
            f"Source agent {agent_id} is not available through LAN discovery"
        )

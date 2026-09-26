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

        agent_id, remote_profile = self._split_distributed_profile(
            profile
        )

        client = self._client_for_agent(agent_id)
        return client.get_memory(remote_profile, memory_id)

    def get_memory_metadata(
        self,
        profile: str,
        memory_id: str,
    ) -> dict:
        profile = str(profile)
        memory_id = str(memory_id)

        if ":" not in profile:
            return self._local.get_memory_metadata(
                profile,
                memory_id,
            )

        agent_id, remote_profile = self._split_distributed_profile(
            profile
        )

        client = self._client_for_agent(agent_id)
        return client.get_memory_metadata(
            remote_profile,
            memory_id,
        )

    @staticmethod
    def _split_distributed_profile(
        profile: str,
    ) -> tuple[str, str]:
        agent_id, remote_profile = profile.split(":", 1)

        if not agent_id or not remote_profile:
            raise KeyError(
                f"Invalid distributed source profile: {profile}"
            )

        return agent_id, remote_profile

    @staticmethod
    def _client_for_agent(
        agent_id: str,
    ) -> AgentMemoryClient:
        for endpoint in get_discovered_agents():
            if endpoint.agent_id == agent_id:
                return AgentMemoryClient(endpoint)

        raise KeyError(
            f"Source agent {agent_id} is not available through LAN discovery"
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .agent_rebuild import AgentEndpoint, AgentMemoryClient
from .collective import CollectiveDAO


@dataclass
class RebuildResult:
    agents_discovered: int = 0
    agents_contacted: int = 0
    profiles_discovered: int = 0
    memories_discovered: int = 0
    entries_created: int = 0
    entries_promoted: int = 0
    failures: int = 0


class DistributedCollectiveRebuilder:
    """
    Reconstruct the collective from adopted LAN agents.

    This operation never performs the destructive nuke. The Browser exposes
    nuke and rebuild as two distinct operations.
    """

    def __init__(self, dao: CollectiveDAO | None = None):
        self.dao = dao or CollectiveDAO()

    def rebuild(self, agents: Iterable[AgentEndpoint]) -> RebuildResult:
        agents = list(agents)
        result = RebuildResult(agents_discovered=len(agents))

        for agent in agents:
            try:
                client = AgentMemoryClient(agent)
                inventory = client.inventory()
                result.agents_contacted += 1

                for profile in inventory.get("profiles", []):
                    profile_name = profile.get("profile")
                    if not profile_name:
                        result.failures += 1
                        continue

                    result.profiles_discovered += 1

                    for memory in profile.get("memories", []):
                        memory_id = memory.get("memory_id")
                        if memory_id is None:
                            result.failures += 1
                            continue

                        result.memories_discovered += 1
                        source_profile = f"{agent.agent_id}:{profile_name}"

                        try:
                            existing = self.dao.get_by_source(
                                source_profile,
                                str(memory_id),
                            )
                            if existing is None:
                                entry_id = self.dao.insert_collective_entry(
                                    source_profile,
                                    str(memory_id),
                                )
                                self.dao.update_entry_promoted(entry_id)
                                result.entries_created += 1
                                result.entries_promoted += 1
                        except Exception:
                            result.failures += 1

            except Exception:
                result.failures += 1

        return result

    def close(self) -> None:
        self.dao.close()

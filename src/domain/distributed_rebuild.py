from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .agent_rebuild import AgentEndpoint, AgentMemoryClient
from .collective_rebuild import (
    CollectiveRebuilder,
    RebuildResult,
)


class DistributedCollectiveRebuilder:
    """
    Rebuild the collective from all currently discovered agents.

    Discovery tells us which machines exist.
    Each machine supplies references to its own Mnemosyne memories.
    """

    def __init__(
        self,
        rebuilder: CollectiveRebuilder | None = None,
    ) -> None:
        self.rebuilder = rebuilder or CollectiveRebuilder()

    def rebuild(
        self,
        agents: Iterable[AgentEndpoint],
    ) -> RebuildResult:

        agents = list(agents)

        result = RebuildResult(
            agents_discovered=len(agents),
        )

        # The destructive operation happens exactly once.
        self.rebuilder.nuke()

        for agent in agents:
            try:
                client = AgentMemoryClient(agent)
                inventory = client.inventory()

                result.agents_contacted += 1

                profiles = inventory.get("profiles", [])

                for profile in profiles:
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

                        # Include the originating agent in the provenance
                        # namespace so two machines can safely have the
                        # same profile/memory ID.
                        source_profile = (
                            f"{agent.agent_id}:{profile_name}"
                        )

                        try:
                            _, created = (
                                self.rebuilder.add_memory_reference(
                                    source_profile,
                                    str(memory_id),
                                )
                            )

                            if created:
                                result.entries_created += 1
                                result.entries_promoted += 1

                        except Exception:
                            result.failures += 1

            except Exception:
                result.failures += 1

        return result
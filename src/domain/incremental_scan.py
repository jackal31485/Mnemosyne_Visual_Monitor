from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from src.domain.agent_rebuild import AgentEndpoint, AgentMemoryClient
from src.domain.collective import CollectiveDAO


@dataclass
class AgentScanResult:
    agent_id: str
    hostname: str
    success: bool = True
    memories_discovered: int = 0
    already_known: int = 0
    new_memories: int = 0
    entries_created: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IncrementalScanResult:
    agents_scanned: int = 0
    agents_failed: int = 0
    memories_discovered: int = 0
    memories_existing: int = 0
    memories_new: int = 0
    entries_created: int = 0
    created_entry_ids: list[int] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    agents: list[AgentScanResult] = field(default_factory=list)


class IncrementalCollectiveScanner:
    """
    Incrementally import memories from adopted LAN agents.

    This operation is strictly additive:

    - It never deletes collective entries.
    - It never resets agent adoption state.
    - It only inserts references that do not already exist.
    - Existing collective entries are left untouched.
    """

    def __init__(self, dao: CollectiveDAO):
        self.dao = dao

    def scan(
        self,
        agents: Iterable[AgentEndpoint],
    ) -> IncrementalScanResult:
        agents = list(agents)

        result = IncrementalScanResult(
            agents_scanned=len(agents),
        )

        for agent in agents:
            agent_result = AgentScanResult(
                agent_id=agent.agent_id,
                hostname=agent.hostname,
            )

            try:
                client = AgentMemoryClient(agent)
                inventory = client.inventory()

                for profile in inventory.get("profiles", []):
                    profile_name = profile.get("profile")

                    if not profile_name:
                        failure = {
                            "agent_id": agent.agent_id,
                            "hostname": agent.hostname,
                            "error": "Inventory contained a profile without a name",
                        }
                        agent_result.failures.append(failure)
                        result.failures.append(failure)
                        continue

                    source_profile = (
                        f"{agent.agent_id}:{profile_name}"
                    )

                    for memory in profile.get("memories", []):
                        memory_id = memory.get("memory_id")

                        if memory_id is None:
                            failure = {
                                "agent_id": agent.agent_id,
                                "hostname": agent.hostname,
                                "profile": profile_name,
                                "error": (
                                    "Inventory contained a memory "
                                    "without a memory_id"
                                ),
                            }
                            agent_result.failures.append(failure)
                            result.failures.append(failure)
                            continue

                        memory_id = str(memory_id)

                        result.memories_discovered += 1
                        agent_result.memories_discovered += 1

                        existing = self.dao.get_by_source(
                            source_profile,
                            memory_id,
                        )

                        if existing is not None:
                            result.memories_existing += 1
                            agent_result.already_known += 1
                            continue

                        try:
                            entry_id = self.dao.insert_collective_entry(
                                source_profile=source_profile,
                                origin_memory_id=memory_id,
                            )

                            result.created_entry_ids.append(entry_id)

                            result.memories_new += 1
                            result.entries_created += 1

                            agent_result.new_memories += 1
                            agent_result.entries_created += 1

                        except Exception as exc:
                            failure = {
                                "agent_id": agent.agent_id,
                                "hostname": agent.hostname,
                                "profile": profile_name,
                                "memory_id": memory_id,
                                "stage": "import",
                                "error": str(exc),
                            }

                            agent_result.failures.append(failure)
                            result.failures.append(failure)

            except Exception as exc:
                agent_result.success = False
                result.agents_failed += 1

                failure = {
                    "agent_id": agent.agent_id,
                    "hostname": agent.hostname,
                    "stage": "inventory",
                    "error": str(exc),
                }

                agent_result.failures.append(failure)
                result.failures.append(failure)

            result.agents.append(agent_result)

        return result

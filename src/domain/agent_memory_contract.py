from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentMemoryReference:
    """
    A reference to an agent-owned Mnemosyne memory.

    Raw memory content is intentionally NOT part of the collective
    representation.
    """

    agent_id: str
    hostname: str
    profile: str
    memory_id: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        agent_id: str,
        hostname: str,
    ) -> "AgentMemoryReference":
        profile = data.get("profile")
        memory_id = data.get("memory_id")

        if not isinstance(profile, str) or not profile:
            raise ValueError("memory reference requires profile")

        if memory_id is None:
            raise ValueError("memory reference requires memory_id")

        return cls(
            agent_id=agent_id,
            hostname=hostname,
            profile=profile,
            memory_id=str(memory_id),
        )
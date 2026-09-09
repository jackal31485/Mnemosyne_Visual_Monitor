from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen
import json


@dataclass(frozen=True)
class AgentEndpoint:
    agent_id: str
    hostname: str
    base_url: str


class AgentMemoryClient:
    """Read-only HTTP client for an adopted Mnemosyne agent."""

    def __init__(self, endpoint: AgentEndpoint, timeout: float = 5.0):
        self.endpoint = endpoint
        self.timeout = timeout

    def _get_json(self, path: str) -> dict[str, Any]:
        url = self.endpoint.base_url.rstrip("/") + path
        request = Request(
            url,
            method="GET",
            headers={"Accept": "application/json"},
        )

        with urlopen(request, timeout=self.timeout) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Agent {self.endpoint.hostname} returned "
                    f"HTTP {response.status}"
                )

            return json.loads(
                response.read().decode("utf-8")
            )

    def inventory(self) -> dict[str, Any]:
        return self._get_json("/api/memories/inventory")

    def get_memory(
        self,
        profile: str,
        memory_id: str,
    ) -> str:
        data = self._get_json(
            f"/api/memories/{_quote(profile)}/{_quote(memory_id)}"
        )

        content = data.get("content")

        if not isinstance(content, str):
            raise KeyError(
                f"Memory {memory_id} not available for profile {profile}"
            )

        return content

    def get_memory_metadata(
        self,
        profile: str,
        memory_id: str,
    ) -> dict[str, Any]:
        """Retrieve temporal source metadata from an adopted agent."""
        data = self._get_json(
            f"/api/memories/{_quote(profile)}/{_quote(memory_id)}"
        )

        return {
            "event_date": data.get("event_date"),
            "event_date_precision": data.get(
                "event_date_precision"
            ),
            "timestamp": data.get("timestamp"),
            "created_at": data.get("created_at"),
        }


def _quote(value: str) -> str:
    from urllib.parse import quote

    return quote(str(value), safe="")

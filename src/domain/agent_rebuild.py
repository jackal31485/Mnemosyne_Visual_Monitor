from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen
import json


@dataclass
class AgentEndpoint:
    agent_id: str
    hostname: str
    base_url: str


class AgentMemoryClient:
    """
    Read-only client for the memory inventory exposed by an agent.

    This client only requests references. It never writes to the
    remote Mnemosyne database.
    """

    def __init__(
        self,
        endpoint: AgentEndpoint,
        timeout: float = 5.0,
    ) -> None:
        self.endpoint = endpoint
        self.timeout = timeout

    def inventory(self) -> dict[str, Any]:
        url = (
            self.endpoint.base_url.rstrip("/")
            + "/api/memories/inventory"
        )

        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
            },
        )

        with urlopen(request, timeout=self.timeout) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Agent returned HTTP {response.status}"
                )

            payload = response.read()

        return json.loads(payload.decode("utf-8"))
from __future__ import annotations

import pytest

from src.domain.agent_rebuild import AgentEndpoint
from src.domain.distributed_memory_gateway import DistributedMemoryGateway


def test_local_profile_uses_local_gateway(monkeypatch):
    calls = []

    class FakeLocalGateway:
        def get_memory(self, profile, memory_id):
            calls.append((profile, memory_id))
            return "local memory"

    gateway = DistributedMemoryGateway()
    gateway._local = FakeLocalGateway()

    result = gateway.get_memory("athena", "memory-1")

    assert result == "local memory"
    assert calls == [("athena", "memory-1")]


def test_qualified_profile_routes_to_matching_agent(monkeypatch):
    endpoint = AgentEndpoint(
        agent_id="agent-a",
        hostname="agent-a-host",
        base_url="http://agent-a.test",
    )

    calls = []

    class FakeClient:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def get_memory(self, profile, memory_id):
            calls.append(
                (self.endpoint.agent_id, profile, memory_id)
            )
            return "remote memory"

    monkeypatch.setattr(
        "src.domain.distributed_memory_gateway.get_discovered_agents",
        lambda: [endpoint],
    )
    monkeypatch.setattr(
        "src.domain.distributed_memory_gateway.AgentMemoryClient",
        FakeClient,
    )

    gateway = DistributedMemoryGateway()

    result = gateway.get_memory(
        "agent-a:horus",
        "memory-1",
    )

    assert result == "remote memory"
    assert calls == [
        ("agent-a", "horus", "memory-1")
    ]


def test_qualified_profile_does_not_fallback_to_local_agent(monkeypatch):
    endpoint = AgentEndpoint(
        agent_id="different-agent",
        hostname="other-host",
        base_url="http://other.test",
    )

    monkeypatch.setattr(
        "src.domain.distributed_memory_gateway.get_discovered_agents",
        lambda: [endpoint],
    )

    gateway = DistributedMemoryGateway()

    with pytest.raises(
        KeyError,
        match="Source agent agent-a is not available",
    ):
        gateway.get_memory(
            "agent-a:athena",
            "memory-1",
        )


def test_invalid_qualified_profile_is_rejected():
    gateway = DistributedMemoryGateway()

    with pytest.raises(
        KeyError,
        match="Invalid distributed source profile",
    ):
        gateway.get_memory(
            ":athena",
            "memory-1",
        )

    with pytest.raises(
        KeyError,
        match="Invalid distributed source profile",
    ):
        gateway.get_memory(
            "agent-a:",
            "memory-1",
        )

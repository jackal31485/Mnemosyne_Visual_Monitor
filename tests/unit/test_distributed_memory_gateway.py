from __future__ import annotations

import pytest

from src.domain.agent_rebuild import AgentEndpoint
from src.domain.distributed_memory_gateway import DistributedMemoryGateway


def test_local_profile_uses_local_gateway(monkeypatch):
    calls = []

    class FakeLocalGateway:
        def get_memory(self, profile, memory_id):
            calls.append(("content", profile, memory_id))
            return "local memory"

    gateway = DistributedMemoryGateway()
    gateway._local = FakeLocalGateway()

    result = gateway.get_memory("athena", "memory-1")

    assert result == "local memory"
    assert calls == [("content", "athena", "memory-1")]


def test_local_profile_uses_local_metadata_gateway():
    calls = []

    class FakeLocalGateway:
        def get_memory_metadata(self, profile, memory_id):
            calls.append((profile, memory_id))
            return {
                "event_date": "2026-09-26",
                "event_date_precision": "day",
                "timestamp": "2026-09-26T12:00:00",
                "created_at": "2026-09-26T12:00:00",
            }

    gateway = DistributedMemoryGateway()
    gateway._local = FakeLocalGateway()

    result = gateway.get_memory_metadata(
        "athena",
        "memory-1",
    )

    assert result["event_date"] == "2026-09-26"
    assert result["event_date_precision"] == "day"
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
                ("content", self.endpoint.agent_id, profile, memory_id)
            )
            return "remote memory"

        def get_memory_metadata(self, profile, memory_id):
            calls.append(
                ("metadata", self.endpoint.agent_id, profile, memory_id)
            )
            return {
                "event_date": "2026-09-26",
                "event_date_precision": "day",
                "timestamp": None,
                "created_at": None,
            }

    monkeypatch.setattr(
        "src.domain.distributed_memory_gateway.get_discovered_agents",
        lambda: [endpoint],
    )
    monkeypatch.setattr(
        "src.domain.distributed_memory_gateway.AgentMemoryClient",
        FakeClient,
    )

    gateway = DistributedMemoryGateway()

    assert gateway.get_memory(
        "agent-a:horus",
        "memory-1",
    ) == "remote memory"

    assert gateway.get_memory_metadata(
        "agent-a:horus",
        "memory-1",
    )["event_date"] == "2026-09-26"

    assert calls == [
        ("content", "agent-a", "horus", "memory-1"),
        ("metadata", "agent-a", "horus", "memory-1"),
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


def test_local_profile_cannot_cross_read_another_profile():
    calls = []

    class FakeLocalGateway:
        def get_memory(self, profile, memory_id):
            calls.append((profile, memory_id))
            if profile == "profile-a":
                return "profile-a memory"
            raise KeyError(
                f"Memory {memory_id} not found for profile {profile}"
            )

    gateway = DistributedMemoryGateway()
    gateway._local = FakeLocalGateway()

    assert gateway.get_memory("profile-a", "memory-1") == "profile-a memory"

    with pytest.raises(
        KeyError,
        match="Memory memory-1 not found for profile profile-b",
    ):
        gateway.get_memory("profile-b", "memory-1")

    assert calls == [
        ("profile-a", "memory-1"),
        ("profile-b", "memory-1"),
    ]

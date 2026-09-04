from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.domain.agent_rebuild import AgentEndpoint
from src.domain.collective import CollectiveDAO


client = TestClient(app)


class FakeMemoryClient:
    inventories = {}

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def inventory(self):
        return self.inventories[self.endpoint.agent_id]

    def get_memory(self, profile, memory_id):
        memories = self.inventories[self.endpoint.agent_id]["memories"]
        return memories[(profile, str(memory_id))]


@pytest.fixture
def fake_agent():
    return AgentEndpoint(
        agent_id="agent-a",
        hostname="agent-a-host",
        base_url="http://agent-a.test",
    )


@pytest.fixture
def isolated_collective(monkeypatch, tmp_path):
    db_path = tmp_path / "collective.db"

    monkeypatch.setattr(
        "app.routes.admin.COLLECTIVE_DB",
        db_path,
    )

    return db_path


def _dao(db_path: Path) -> CollectiveDAO:
    dao = CollectiveDAO(db_path)
    dao.ensure_schema()
    return dao


def _inventory(*memory_ids):
    return {
        "profiles": [
            {
                "profile": "horus",
                "memories": [
                    {"memory_id": str(memory_id)}
                    for memory_id in memory_ids
                ],
            }
        ]
    }


def test_scan_imports_new_memories_and_rebuilds_graph(
    monkeypatch,
    isolated_collective,
    fake_agent,
):
    FakeMemoryClient.inventories = {
        "agent-a": _inventory("1", "2"),
    }

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FakeMemoryClient,
    )
    monkeypatch.setattr(
        "app.routes.admin.get_discovered_agents",
        lambda: [fake_agent],
    )

    graph_calls = []

    monkeypatch.setattr(
        "app.routes.admin._rebuild_graph",
        lambda: graph_calls.append(True)
        or {"rebuilt": True, "result": {"nodes": 2}},
    )

    class FakeGateway:
        def get_memory(self, profile, memory_id):
            return f"memory {profile} {memory_id}"

    monkeypatch.setattr(
        "app.routes.admin.DistributedMemoryGateway",
        FakeGateway,
    )

    response = client.post("/api/admin/collective/scan")

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["operation"] == "scan"
    assert body["agents_scanned"] == 1
    assert body["agents_failed"] == 0
    assert body["memories_discovered"] == 2
    assert body["memories_existing"] == 0
    assert body["memories_new"] == 2
    assert body["entries_created"] == 2
    assert body["embedding_failures"] == []
    assert body["failures"] == []

    assert len(graph_calls) == 1

    assert body["collective"]["total_entries"] == 2
    assert body["collective"]["promoted"] == 2
    assert body["collective"]["embedded"] == 2

    assert body["agents"][0]["agent_id"] == "agent-a"
    assert body["agents"][0]["success"] is True
    assert body["agents"][0]["new_memories"] == 2

    dao = _dao(isolated_collective)
    rows = dao.conn.execute(
        """
        SELECT source_profile, origin_memory_id, is_promoted, embedding
        FROM collective_entries
        ORDER BY id
        """
    ).fetchall()

    assert [
        (
            row["source_profile"],
            row["origin_memory_id"],
            row["is_promoted"],
            row["embedding"] is not None,
        )
        for row in rows
    ] == [
        ("agent-a:horus", "1", 1, True),
        ("agent-a:horus", "2", 1, True),
    ]

    dao.close()


def test_scan_does_not_modify_existing_entries(
    monkeypatch,
    isolated_collective,
    fake_agent,
):
    FakeMemoryClient.inventories = {
        "agent-a": _inventory("1", "2"),
    }

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FakeMemoryClient,
    )
    monkeypatch.setattr(
        "app.routes.admin.get_discovered_agents",
        lambda: [fake_agent],
    )

    dao = _dao(isolated_collective)

    existing_id = dao.insert_collective_entry(
        source_profile="agent-a:horus",
        origin_memory_id="1",
    )

    dao.conn.execute(
        """
        UPDATE collective_entries
        SET is_promoted = 0
        WHERE id = ?
        """,
        (existing_id,),
    )
    dao.conn.commit()

    original = dao.conn.execute(
        """
        SELECT source_profile, origin_memory_id, is_promoted, embedding
        FROM collective_entries
        WHERE id = ?
        """,
        (existing_id,),
    ).fetchone()

    dao.close()

    monkeypatch.setattr(
        "app.routes.admin._rebuild_graph",
        lambda: {"rebuilt": True},
    )

    class FakeGateway:
        def get_memory(self, profile, memory_id):
            return f"new memory {profile} {memory_id}"

    monkeypatch.setattr(
        "app.routes.admin.DistributedMemoryGateway",
        FakeGateway,
    )

    response = client.post("/api/admin/collective/scan")

    assert response.status_code == 200

    body = response.json()

    assert body["memories_existing"] == 1
    assert body["memories_new"] == 1
    assert body["entries_created"] == 1

    dao = _dao(isolated_collective)

    current = dao.conn.execute(
        """
        SELECT source_profile, origin_memory_id, is_promoted, embedding
        FROM collective_entries
        WHERE id = ?
        """,
        (existing_id,),
    ).fetchone()

    assert tuple(current) == tuple(original)

    count = dao.conn.execute(
        "SELECT COUNT(*) FROM collective_entries"
    ).fetchone()[0]

    assert count == 2

    dao.close()


def test_second_scan_is_idempotent_and_skips_graph_rebuild(
    monkeypatch,
    isolated_collective,
    fake_agent,
):
    FakeMemoryClient.inventories = {
        "agent-a": _inventory("1", "2"),
    }

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FakeMemoryClient,
    )
    monkeypatch.setattr(
        "app.routes.admin.get_discovered_agents",
        lambda: [fake_agent],
    )

    graph_calls = []

    monkeypatch.setattr(
        "app.routes.admin._rebuild_graph",
        lambda: graph_calls.append(True)
        or {"rebuilt": True},
    )

    class FakeGateway:
        calls = 0

        def get_memory(self, profile, memory_id):
            self.calls += 1
            return f"memory {profile} {memory_id}"

    gateway = FakeGateway()

    monkeypatch.setattr(
        "app.routes.admin.DistributedMemoryGateway",
        lambda: gateway,
    )

    first = client.post("/api/admin/collective/scan")
    second = client.post("/api/admin/collective/scan")

    assert first.status_code == 200
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()

    assert first_body["memories_new"] == 2
    assert first_body["entries_created"] == 2

    assert second_body["memories_discovered"] == 2
    assert second_body["memories_existing"] == 2
    assert second_body["memories_new"] == 0
    assert second_body["entries_created"] == 0
    assert second_body["embedding_failures"] == []

    assert len(graph_calls) == 1
    assert gateway.calls == 2


def test_scan_isolates_agent_failure(
    monkeypatch,
    isolated_collective,
):
    good_agent = AgentEndpoint(
        agent_id="good-agent",
        hostname="good-host",
        base_url="http://good.test",
    )
    bad_agent = AgentEndpoint(
        agent_id="bad-agent",
        hostname="bad-host",
        base_url="http://bad.test",
    )

    class MixedClient:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def inventory(self):
            if self.endpoint.agent_id == "bad-agent":
                raise RuntimeError("simulated agent failure")
            return _inventory("10")

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        MixedClient,
    )
    monkeypatch.setattr(
        "app.routes.admin.get_discovered_agents",
        lambda: [good_agent, bad_agent],
    )

    monkeypatch.setattr(
        "app.routes.admin._rebuild_graph",
        lambda: {"rebuilt": True},
    )

    class FakeGateway:
        def get_memory(self, profile, memory_id):
            return f"memory {profile} {memory_id}"

    monkeypatch.setattr(
        "app.routes.admin.DistributedMemoryGateway",
        FakeGateway,
    )

    response = client.post("/api/admin/collective/scan")

    assert response.status_code == 200

    body = response.json()

    assert body["agents_scanned"] == 2
    assert body["agents_failed"] == 1
    assert body["memories_new"] == 1
    assert body["entries_created"] == 1

    good = next(
        agent
        for agent in body["agents"]
        if agent["agent_id"] == "good-agent"
    )
    bad = next(
        agent
        for agent in body["agents"]
        if agent["agent_id"] == "bad-agent"
    )

    assert good["success"] is True
    assert good["new_memories"] == 1

    assert bad["success"] is False
    assert bad["failures"]

    dao = _dao(isolated_collective)

    count = dao.conn.execute(
        "SELECT COUNT(*) FROM collective_entries"
    ).fetchone()[0]

    assert count == 1

    dao.close()


def test_scan_without_adopted_agents_returns_409(
    monkeypatch,
    isolated_collective,
):
    monkeypatch.setattr(
        "app.routes.admin.get_discovered_agents",
        lambda: [],
    )

    response = client.post("/api/admin/collective/scan")

    assert response.status_code == 409
    assert "No adopted online LAN agents" in response.json()["detail"]

from __future__ import annotations

from src.domain.agent_rebuild import AgentEndpoint
from src.domain.collective import CollectiveDAO
from src.domain.incremental_scan import IncrementalCollectiveScanner


def _agent() -> AgentEndpoint:
    return AgentEndpoint(
        agent_id="agent-a",
        hostname="agent-a-host",
        base_url="http://127.0.0.1:9999",
    )


class FakeClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def inventory(self):
        return {
            "profiles": [
                {
                    "profile": "horus",
                    "memories": [
                        {"memory_id": "1"},
                        {"memory_id": "2"},
                        {"memory_id": "3"},
                    ],
                }
            ]
        }


def test_incremental_scan_imports_only_new_entries(
    monkeypatch,
    tmp_path,
):
    dao = CollectiveDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    dao.insert_collective_entry(
        "agent-a:horus",
        "1",
    )

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FakeClient,
    )

    scanner = IncrementalCollectiveScanner(dao)

    result = scanner.scan([_agent()])

    assert result.agents_scanned == 1
    assert result.agents_failed == 0
    assert result.memories_discovered == 3
    assert result.memories_existing == 1
    assert result.memories_new == 2
    assert result.entries_created == 2
    assert len(result.created_entry_ids) == 2

    created_rows = dao.conn.execute(
        """
        SELECT id
        FROM collective_entries
        WHERE origin_memory_id IN ('2', '3')
        ORDER BY id
        """
    ).fetchall()

    assert result.created_entry_ids == [
        row["id"] for row in created_rows
    ]

    rows = dao.conn.execute(
        """
        SELECT source_profile, origin_memory_id
        FROM collective_entries
        ORDER BY origin_memory_id
        """
    ).fetchall()

    assert [
        (row["source_profile"], row["origin_memory_id"])
        for row in rows
    ] == [
        ("agent-a:horus", "1"),
        ("agent-a:horus", "2"),
        ("agent-a:horus", "3"),
    ]

    dao.close()


def test_incremental_scan_is_idempotent(
    monkeypatch,
    tmp_path,
):
    dao = CollectiveDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FakeClient,
    )

    scanner = IncrementalCollectiveScanner(dao)

    first = scanner.scan([_agent()])
    second = scanner.scan([_agent()])

    assert first.memories_new == 3
    assert first.entries_created == 3

    assert second.memories_discovered == 3
    assert second.memories_existing == 3
    assert second.memories_new == 0
    assert second.entries_created == 0
    assert second.created_entry_ids == []

    count = dao.conn.execute(
        "SELECT COUNT(*) FROM collective_entries"
    ).fetchone()[0]

    assert count == 3

    dao.close()


def test_incremental_scan_does_not_modify_existing_entry(
    monkeypatch,
    tmp_path,
):
    dao = CollectiveDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    entry_id = dao.insert_collective_entry(
        "agent-a:horus",
        "1",
    )

    dao.conn.execute(
        """
        UPDATE collective_entries
        SET is_promoted = 1,
            validator_profile = 'athena',
            validation_score = 0.91
        WHERE id = ?
        """,
        (entry_id,),
    )
    dao.conn.commit()

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FakeClient,
    )

    scanner = IncrementalCollectiveScanner(dao)
    result = scanner.scan([_agent()])

    assert result.memories_new == 2

    row = dao.conn.execute(
        """
        SELECT is_promoted, validator_profile, validation_score
        FROM collective_entries
        WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()

    assert row["is_promoted"] == 1
    assert row["validator_profile"] == "athena"
    assert row["validation_score"] == 0.91

    dao.close()


def test_incremental_scan_reports_agent_failure(
    monkeypatch,
    tmp_path,
):
    class FailingClient:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def inventory(self):
            raise RuntimeError("agent unavailable")

    monkeypatch.setattr(
        "src.domain.incremental_scan.AgentMemoryClient",
        FailingClient,
    )

    dao = CollectiveDAO(tmp_path / "collective.db")
    dao.ensure_schema()
    scanner = IncrementalCollectiveScanner(dao)

    result = scanner.scan([_agent()])

    assert result.agents_scanned == 1
    assert result.agents_failed == 1
    assert result.memories_discovered == 0
    assert result.entries_created == 0
    assert len(result.failures) == 1
    assert "agent unavailable" in result.failures[0]["error"]

    dao.close()

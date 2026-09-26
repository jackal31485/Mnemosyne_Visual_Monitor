import sqlite3
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routes.discovery import DISCOVERY_DB_PATH


client = TestClient(app)


def _insert_agent(
    client_id: str,
    hostname: str = "test-host",
    version: str = "1.0.0",
    state: str = "DISCOVERED",
) -> None:
    with sqlite3.connect(str(DISCOVERY_DB_PATH)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO discovery_records
            (
                client_id,
                hostname,
                installed_version,
                first_seen,
                last_seen,
                state
            )
            VALUES (?, ?, ?, 100, 100, ?)
            """,
            (client_id, hostname, version, state),
        )


def _delete_agent(client_id: str) -> None:
    with sqlite3.connect(str(DISCOVERY_DB_PATH)) as conn:
        conn.execute(
            "DELETE FROM discovery_records WHERE client_id=?",
            (client_id,),
        )


def test_adopt_discovered_agent():
    client_id = str(uuid.uuid4())

    try:
        _insert_agent(client_id)

        response = client.post(
            f"/api/discovery/{client_id}/adopt"
        )

        assert response.status_code == 200

        body = response.json()

        assert body["adopted"] is True
        assert body["agent"]["client_id"] == client_id
        assert body["agent"]["state"] == "ADOPTED"

        with sqlite3.connect(str(DISCOVERY_DB_PATH)) as conn:
            row = conn.execute(
                "SELECT state FROM discovery_records WHERE client_id=?",
                (client_id,),
            ).fetchone()

        assert row == ("ADOPTED",)

    finally:
        _delete_agent(client_id)


def test_adoption_is_idempotent():
    client_id = str(uuid.uuid4())

    try:
        _insert_agent(client_id)

        first = client.post(
            f"/api/discovery/{client_id}/adopt"
        )
        second = client.post(
            f"/api/discovery/{client_id}/adopt"
        )

        assert first.status_code == 200
        assert second.status_code == 200

        assert first.json()["adopted"] is True
        assert second.json()["adopted"] is False

        assert second.json()["agent"]["state"] == "ADOPTED"

    finally:
        _delete_agent(client_id)


def test_adopt_missing_agent_returns_404():
    client_id = str(uuid.uuid4())

    _delete_agent(client_id)

    response = client.post(
        f"/api/discovery/{client_id}/adopt"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Discovery agent not found"


def test_adoption_does_not_create_profile_or_memory():
    client_id = str(uuid.uuid4())

    try:
        _insert_agent(client_id)

        response = client.post(
            f"/api/discovery/{client_id}/adopt"
        )

        assert response.status_code == 200

        # B1 only changes discovery lifecycle state.
        # There must be no profile_id or memory_id in the response.
        agent = response.json()["agent"]

        assert "profile_id" not in agent
        assert "memory_id" not in agent

    finally:
        _delete_agent(client_id)


def test_adopted_agent_remains_discoverable(monkeypatch):
    client_id = str(uuid.uuid4())

    class FakeBeacon:
        def __init__(self, client_id):
            self.client_id = client_id

    monkeypatch.setattr(
        "app.routes.discovery.DiscoveryBeacon",
        lambda: FakeBeacon(client_id),
    )

    try:
        _insert_agent(client_id)

        adopt = client.post(
            f"/api/discovery/{client_id}/adopt"
        )

        assert adopt.status_code == 200

        listing = client.get("/api/discovery")

        assert listing.status_code == 200

        agents = listing.json()["agents"]

        matching = [
            agent
            for agent in agents
            if agent["client_id"] == client_id
        ]

        assert len(matching) == 1
        assert matching[0]["state"] == "ADOPTED"
        assert matching[0]["is_local"] is True

    finally:
        _delete_agent(client_id)

import sqlite3

from app.services import discovered_agents


def test_local_adopted_agent_uses_loopback_endpoint(tmp_path, monkeypatch):
    db_path = tmp_path / "discovery.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE discovery_records (
                client_id TEXT PRIMARY KEY,
                hostname TEXT,
                installed_version TEXT,
                address TEXT,
                api_port INTEGER,
                first_seen INTEGER,
                last_seen INTEGER,
                state TEXT NOT NULL DEFAULT 'DISCOVERED'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO discovery_records (
                client_id,
                hostname,
                installed_version,
                address,
                api_port,
                first_seen,
                last_seen,
                state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "local-client",
                "loki-tux",
                "0.20.0",
                "192.168.2.181",
                8000,
                1,
                2,
                "ADOPTED",
            ),
        )
        conn.commit()

    class FakeBeacon:
        client_id = "local-client"

    monkeypatch.setattr(
        discovered_agents,
        "DB_PATH",
        db_path,
    )
    monkeypatch.setattr(
        discovered_agents,
        "DiscoveryBeacon",
        lambda: FakeBeacon(),
    )

    agents = discovered_agents.get_discovered_agents()

    assert len(agents) == 1
    assert agents[0].agent_id == "local-client"
    assert agents[0].hostname == "loki-tux"
    assert agents[0].base_url == "http://127.0.0.1:8000"


def test_remote_adopted_agent_keeps_advertised_endpoint(tmp_path, monkeypatch):
    db_path = tmp_path / "discovery.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE discovery_records (
                client_id TEXT PRIMARY KEY,
                hostname TEXT,
                installed_version TEXT,
                address TEXT,
                api_port INTEGER,
                first_seen INTEGER,
                last_seen INTEGER,
                state TEXT NOT NULL DEFAULT 'DISCOVERED'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO discovery_records (
                client_id,
                hostname,
                installed_version,
                address,
                api_port,
                first_seen,
                last_seen,
                state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "remote-client",
                "remote-host",
                "0.20.0",
                "192.168.2.200",
                8000,
                1,
                2,
                "ADOPTED",
            ),
        )
        conn.commit()

    class FakeBeacon:
        client_id = "local-client"

    monkeypatch.setattr(
        discovered_agents,
        "DB_PATH",
        db_path,
    )
    monkeypatch.setattr(
        discovered_agents,
        "DiscoveryBeacon",
        lambda: FakeBeacon(),
    )

    agents = discovered_agents.get_discovered_agents()

    assert len(agents) == 1
    assert agents[0].agent_id == "remote-client"
    assert agents[0].base_url == "http://192.168.2.200:8000"

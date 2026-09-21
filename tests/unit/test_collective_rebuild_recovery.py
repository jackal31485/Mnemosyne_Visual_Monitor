import sqlite3

import pytest

from src.domain.collective import CollectiveDAO
from src.domain import collective_rebuild


def _create_live_collective(path, profile="legacy", memory_id="old-memory"):
    dao = CollectiveDAO(path)
    dao.ensure_schema()
    dao.insert_collective_entry(
        source_profile=profile,
        origin_memory_id=memory_id,
    )
    dao.close()


def _read_entries(path):
    dao = CollectiveDAO(path)
    dao.ensure_schema()
    rows = dao.conn.execute(
        """
        SELECT source_profile, origin_memory_id
        FROM collective_entries
        ORDER BY id
        """
    ).fetchall()
    dao.close()
    return [(row["source_profile"], row["origin_memory_id"]) for row in rows]


def test_successful_rebuild_atomically_replaces_existing_collective(
    tmp_path,
    monkeypatch,
):
    live_path = tmp_path / "collective.db"
    _create_live_collective(live_path)

    profile_one = tmp_path / "Athena"
    profile_two = tmp_path / "Horus"

    profiles = [profile_one, profile_two]

    def fake_discover():
        return profiles

    def fake_extract(db_path):
        if db_path.parent.parent.parent.name == "Athena":
            return [{"id": "athena-memory"}]
        return [{"id": "horus-memory"}]

    monkeypatch.setattr(
        collective_rebuild,
        "DB_PATH",
        live_path,
    )
    monkeypatch.setattr(
        collective_rebuild,
        "discover_profile_paths",
        fake_discover,
    )
    monkeypatch.setattr(
        collective_rebuild,
        "extract_memories",
        fake_extract,
    )

    result = collective_rebuild.nuke_and_rebuild_collective()

    assert result == {
        "profiles": 2,
        "profile_counts": {
            "Athena": 1,
            "Horus": 1,
        },
        "total_entries": 2,
    }

    assert _read_entries(live_path) == [
        ("Athena", "athena-memory"),
        ("Horus", "horus-memory"),
    ]

    assert not list(tmp_path.glob(".collective.db.*.rebuild"))


def test_failed_rebuild_preserves_existing_collective(
    tmp_path,
    monkeypatch,
):
    live_path = tmp_path / "collective.db"
    _create_live_collective(
        live_path,
        profile="existing-profile",
        memory_id="existing-memory",
    )

    profile_one = tmp_path / "Athena"
    profile_two = tmp_path / "Horus"

    def fake_discover():
        return [profile_one, profile_two]

    def fake_extract(db_path):
        if db_path.parent.parent.parent.name == "Athena":
            return [{"id": "new-memory"}]

        raise sqlite3.DatabaseError("simulated source failure")

    monkeypatch.setattr(
        collective_rebuild,
        "DB_PATH",
        live_path,
    )
    monkeypatch.setattr(
        collective_rebuild,
        "discover_profile_paths",
        fake_discover,
    )
    monkeypatch.setattr(
        collective_rebuild,
        "extract_memories",
        fake_extract,
    )

    with pytest.raises(sqlite3.DatabaseError, match="simulated source failure"):
        collective_rebuild.nuke_and_rebuild_collective()

    assert live_path.exists()
    assert _read_entries(live_path) == [
        ("existing-profile", "existing-memory"),
    ]

    assert not list(tmp_path.glob(".collective.db.*.rebuild"))


def test_failed_rebuild_does_not_modify_existing_database_file(
    tmp_path,
    monkeypatch,
):
    live_path = tmp_path / "collective.db"
    _create_live_collective(
        live_path,
        profile="existing-profile",
        memory_id="existing-memory",
    )

    before = live_path.read_bytes()

    profile = tmp_path / "Broken"

    def fake_discover():
        return [profile]

    def fake_extract(db_path):
        raise OSError("simulated profile read failure")

    monkeypatch.setattr(
        collective_rebuild,
        "DB_PATH",
        live_path,
    )
    monkeypatch.setattr(
        collective_rebuild,
        "discover_profile_paths",
        fake_discover,
    )
    monkeypatch.setattr(
        collective_rebuild,
        "extract_memories",
        fake_extract,
    )

    with pytest.raises(OSError, match="simulated profile read failure"):
        collective_rebuild.nuke_and_rebuild_collective()

    assert live_path.read_bytes() == before
    assert not list(tmp_path.glob(".collective.db.*.rebuild"))

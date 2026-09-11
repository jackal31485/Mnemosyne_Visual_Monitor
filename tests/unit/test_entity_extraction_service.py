from pathlib import Path

import pytest

from src.domain.collective import CollectiveDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.memory_gateway import InMemoryMemoryGateway
from src.services.entity_extraction_service import extract_entities


def make_daos(tmp_path: Path):
    db_path = tmp_path / "collective.db"

    collective_dao = CollectiveDAO(db_path=db_path)
    collective_dao.ensure_schema()

    mention_dao = EntityMentionDAO(db_path=db_path)
    mention_dao.ensure_schema()

    return collective_dao, mention_dao


def promote(dao: CollectiveDAO, entry_id: int) -> None:
    dao.conn.execute(
        """
        UPDATE collective_entries
        SET is_promoted = 1
        WHERE id = ?
        """,
        (entry_id,),
    )
    dao.conn.commit()


def revoke(dao: CollectiveDAO, entry_id: int) -> None:
    dao.conn.execute(
        """
        UPDATE collective_entries
        SET is_revoked = 1
        WHERE id = ?
        """,
        (entry_id,),
    )
    dao.conn.commit()


def test_extracts_mentions_from_promoted_non_revoked_entries(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    entry_id = collective_dao.add_entry(
        "athena",
        "mem-1",
    )
    promote(collective_dao, entry_id)

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"):
                "The Mnemosyne project uses Python and SQLite."
        }
    )

    report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert report.processed == 1
    assert report.mentions_created == 4
    assert report.mentions_existing == 0
    assert report.skipped == 0
    assert report.failures == ()

    mentions = mention_dao.list()

    assert {
        (item["mention_text"], item["entity_type"])
        for item in mentions
    } == {
        ("Mnemosyne", "technology"),
        ("Python", "technology"),
        ("SQLite", "technology"),
        ("The Mnemosyne", "project"),
    }

    assert all(
        item["collective_entry_id"] == entry_id
        for item in mentions
    )
    assert all(
        item["source_profile"] == "athena"
        for item in mentions
    )
    assert all(
        item["source_memory_id"] == "mem-1"
        for item in mentions
    )


def test_unpromoted_entries_are_not_processed(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    entry_id = collective_dao.add_entry(
        "athena",
        "mem-1",
    )

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"):
                "Python SQLite Mnemosyne"
        }
    )

    report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert report.processed == 0
    assert report.mentions_created == 0
    assert report.mentions_existing == 0
    assert report.failures == ()
    assert mention_dao.list() == []

    assert entry_id is not None


def test_revoked_entries_are_not_processed(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    entry_id = collective_dao.add_entry(
        "athena",
        "mem-1",
    )
    promote(collective_dao, entry_id)
    revoke(collective_dao, entry_id)

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"):
                "Python SQLite Mnemosyne"
        }
    )

    report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert report.processed == 0
    assert report.mentions_created == 0
    assert report.mentions_existing == 0
    assert report.failures == ()
    assert mention_dao.list() == []


def test_missing_source_memory_is_reported_and_other_entries_continue(
    tmp_path,
):
    collective_dao, mention_dao = make_daos(tmp_path)

    missing_id = collective_dao.add_entry(
        "athena",
        "missing",
    )
    available_id = collective_dao.add_entry(
        "thoth",
        "available",
    )

    promote(collective_dao, missing_id)
    promote(collective_dao, available_id)

    gateway = InMemoryMemoryGateway(
        {
            ("thoth", "available"):
                "Python and SQLite"
        }
    )

    report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert report.processed == 1
    assert report.mentions_created == 2
    assert report.mentions_existing == 0
    assert report.skipped == 0

    assert len(report.failures) == 1
    failure = report.failures[0]
    assert failure.entry_id == missing_id
    assert failure.source_profile == "athena"
    assert failure.origin_memory_id == "missing"

    mentions = mention_dao.list()

    assert {
        (item["source_profile"], item["source_memory_id"])
        for item in mentions
    } == {
        ("thoth", "available"),
    }


def test_entries_without_entities_are_counted_as_skipped(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    entry_id = collective_dao.add_entry(
        "athena",
        "mem-1",
    )
    promote(collective_dao, entry_id)

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"):
                "plain lowercase text with no known entities"
        }
    )

    report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert report.processed == 1
    assert report.mentions_created == 0
    assert report.mentions_existing == 0
    assert report.skipped == 1
    assert report.failures == ()
    assert mention_dao.list() == []


def test_repeated_extraction_is_idempotent(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    entry_id = collective_dao.add_entry(
        "athena",
        "mem-1",
    )
    promote(collective_dao, entry_id)

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-1"):
                "Python SQLite Mnemosyne"
        }
    )

    first = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    second = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert first.processed == 1
    assert first.mentions_created == 4
    assert first.mentions_existing == 0

    assert second.processed == 1
    assert second.mentions_created == 0
    assert second.mentions_existing == 4

    assert len(mention_dao.list()) == 4
    assert all(
        item["collective_entry_id"] == entry_id
        for item in mention_dao.list()
    )


def test_qualified_profile_identity_is_preserved(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    entry_id = collective_dao.add_entry(
        "agent-a:horus",
        "mem-7",
    )
    promote(collective_dao, entry_id)

    gateway = InMemoryMemoryGateway(
        {
            ("agent-a:horus", "mem-7"):
                "Python"
        }
    )

    report = extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    assert report.failures == ()
    assert report.mentions_created == 1

    mention = mention_dao.list()[0]
    assert mention["source_profile"] == "agent-a:horus"
    assert mention["source_memory_id"] == "mem-7"


def test_source_content_is_not_persisted_in_entity_mentions(tmp_path):
    collective_dao, mention_dao = make_daos(tmp_path)

    secret = "private content that should never be stored here 12345"

    entry_id = collective_dao.add_entry(
        "athena",
        "mem-secret",
    )
    promote(collective_dao, entry_id)

    gateway = InMemoryMemoryGateway(
        {
            ("athena", "mem-secret"):
                f"Python {secret}"
        }
    )

    extract_entities(
        collective_dao,
        mention_dao,
        gateway,
    )

    columns = {
        row["name"]
        for row in mention_dao.conn.execute(
            "PRAGMA table_info(entity_mentions)"
        ).fetchall()
    }

    assert "content" not in columns

    rows = mention_dao.conn.execute(
        "SELECT * FROM entity_mentions"
    ).fetchall()

    assert len(rows) == 1
    assert secret not in str(tuple(rows[0]))

    assert entry_id == rows[0]["collective_entry_id"]

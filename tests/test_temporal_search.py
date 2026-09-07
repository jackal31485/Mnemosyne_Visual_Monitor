from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.domain.collective import CollectiveDAO
from src.domain.live_memory_gateway import LiveMemoryGateway
from src.retrieval.temporal_search import TemporalSearcher


@pytest.fixture
def dao(tmp_path: Path) -> CollectiveDAO:
    dao = CollectiveDAO(tmp_path / "collective.db")
    dao.ensure_schema()

    yield dao

    dao.close()


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    root = tmp_path / "profiles"
    root.mkdir()

    return root


@pytest.fixture
def gateway(source_root: Path) -> LiveMemoryGateway:
    return LiveMemoryGateway(source_root)


def create_source_db(
    source_root: Path,
    profile: str,
    memories: list[dict[str, object]],
) -> None:
    db_path = (
        source_root
        / profile
        / "mnemosyne"
        / "data"
        / "mnemosyne.db"
    )

    db_path.parent.mkdir(parents=True)

    conn = sqlite3.connect(db_path)

    conn.execute(
        """
        CREATE TABLE working_memory (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            event_date TEXT,
            event_date_precision TEXT,
            timestamp TEXT,
            created_at TEXT
        )
        """
    )

    for memory in memories:
        conn.execute(
            """
            INSERT INTO working_memory (
                id,
                content,
                event_date,
                event_date_precision,
                timestamp,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                memory["id"],
                memory.get("content", "test memory"),
                memory.get("event_date"),
                memory.get("event_date_precision", "unknown"),
                memory.get("timestamp"),
                memory.get("created_at"),
            ),
        )

    conn.commit()
    conn.close()


def promote(
    dao: CollectiveDAO,
    profile: str,
    memory_id: str,
) -> int:
    entry_id = dao.add_entry(profile, memory_id)
    dao.update_entry_promoted(entry_id)
    dao.add_provenance(entry_id, profile, memory_id)

    return entry_id


def test_event_date_search_returns_dated_memories(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "memory-a",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
                "timestamp": "2026-08-10T12:00:00",
                "created_at": "2026-08-10 12:00:00",
            },
        ],
    )

    entry_id = promote(dao, "athena", "memory-a")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
    )

    assert [result.entry_id for result in results] == [entry_id]
    assert results[0].source_profile == "athena"
    assert results[0].origin_memory_id == "memory-a"
    assert results[0].date_source == "event_date"
    assert results[0].event_date_precision == "day"
    assert results[0].memory_date == datetime(2026, 8, 10)
    assert results[0].provenance


def test_event_date_window_excludes_outside_dates(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "before",
                "event_date": "2026-07-31",
                "event_date_precision": "day",
            },
            {
                "id": "inside",
                "event_date": "2026-08-15",
                "event_date_precision": "day",
            },
            {
                "id": "after",
                "event_date": "2026-09-01",
                "event_date_precision": "day",
            },
        ],
    )

    before = promote(dao, "athena", "before")
    inside = promote(dao, "athena", "inside")
    after = promote(dao, "athena", "after")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
    )

    assert [result.entry_id for result in results] == [inside]
    assert before not in [result.entry_id for result in results]
    assert after not in [result.entry_id for result in results]


def test_unknown_precision_is_not_treated_as_event_date(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "unknown",
                "event_date": None,
                "event_date_precision": "unknown",
                "timestamp": "2026-08-15T12:00:00",
            },
        ],
    )

    entry_id = promote(dao, "athena", "unknown")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
    )

    assert results == []


def test_recency_uses_recording_time_for_unknown_precision(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "older",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-01T12:00:00",
            },
            {
                "id": "newer",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-20T12:00:00",
            },
        ],
    )

    older = promote(dao, "athena", "older")
    newer = promote(dao, "athena", "newer")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_recency(
        reference_time=datetime(2026, 8, 21, 12, 0, 0),
    )

    assert [result.entry_id for result in results] == [newer, older]
    assert results[0].date_source == "timestamp"


def test_recency_is_deterministic_for_equal_times(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "first",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-20T12:00:00",
            },
            {
                "id": "second",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-20T12:00:00",
            },
        ],
    )

    first = promote(dao, "athena", "first")
    second = promote(dao, "athena", "second")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_recency(
        reference_time=datetime(2026, 8, 21, 12, 0, 0),
    )

    assert [result.entry_id for result in results] == [second, first]


def test_profile_filter(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "athena-memory",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
            },
        ],
    )

    create_source_db(
        source_root,
        "horus",
        [
            {
                "id": "horus-memory",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
            },
        ],
    )

    athena = promote(dao, "athena", "athena-memory")
    horus = promote(dao, "horus", "horus-memory")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
        profile="horus",
    )

    assert [result.entry_id for result in results] == [horus]
    assert athena not in [result.entry_id for result in results]


def test_unpromoted_entries_are_excluded(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "unpromoted",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
            },
        ],
    )

    entry_id = dao.add_entry("athena", "unpromoted")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
    )

    assert entry_id not in [result.entry_id for result in results]


def test_revoked_entries_are_excluded(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "revoked",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
            },
        ],
    )

    entry_id = promote(dao, "athena", "revoked")
    dao.update_entry_revoked(entry_id, "test revocation")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
    )

    assert results == []


def test_missing_source_memory_is_skipped(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
) -> None:
    entry_id = promote(dao, "athena", "missing-memory")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
    )

    assert results == []


def test_limit_is_deterministic(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "first",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
            },
            {
                "id": "second",
                "event_date": "2026-08-10",
                "event_date_precision": "day",
            },
        ],
    )

    first = promote(dao, "athena", "first")
    second = promote(dao, "athena", "second")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_event_date(
        datetime(2026, 8, 1),
        datetime(2026, 8, 31),
        limit=1,
    )

    assert [result.entry_id for result in results] == [first]
    assert second not in [result.entry_id for result in results]


def test_invalid_event_date_window_is_rejected(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
) -> None:
    searcher = TemporalSearcher(dao, gateway)

    with pytest.raises(ValueError):
        searcher.search_by_event_date(
            datetime(2026, 8, 31),
            datetime(2026, 8, 1),
        )


def test_invalid_limit_is_rejected(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
) -> None:
    searcher = TemporalSearcher(dao, gateway)

    with pytest.raises(ValueError):
        searcher.search_by_recency(limit=0)

    with pytest.raises(ValueError):
        searcher.search_by_recency(limit=True)


def test_recency_score_is_bounded_and_monotonic(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "now",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-21T12:00:00",
            },
            {
                "id": "one-day-old",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-20T12:00:00",
            },
            {
                "id": "ten-days-old",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-11T12:00:00",
            },
        ],
    )

    now = promote(dao, "athena", "now")
    one_day_old = promote(dao, "athena", "one-day-old")
    ten_days_old = promote(dao, "athena", "ten-days-old")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_recency(
        reference_time=datetime(2026, 8, 21, 12, 0, 0),
    )

    by_id = {result.entry_id: result for result in results}

    assert 0.0 < by_id[ten_days_old].temporal_score < by_id[one_day_old].temporal_score
    assert by_id[one_day_old].temporal_score < by_id[now].temporal_score
    assert by_id[now].temporal_score == 1.0

    assert all(
        0.0 < result.temporal_score <= 1.0
        for result in results
    )


def test_recency_falls_back_to_created_at(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "created-only",
                "event_date_precision": "unknown",
                "timestamp": None,
                "created_at": "2026-08-20 12:00:00",
            },
        ],
    )

    entry_id = promote(dao, "athena", "created-only")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_recency(
        reference_time=datetime(2026, 8, 21, 12, 0, 0),
    )

    assert [result.entry_id for result in results] == [entry_id]
    assert results[0].date_source == "created_at"
    assert results[0].memory_date == datetime(2026, 8, 20, 12, 0, 0)


def test_malformed_recording_dates_are_skipped(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "bad",
                "event_date_precision": "unknown",
                "timestamp": "not-a-date",
                "created_at": "also-not-a-date",
            },
        ],
    )

    promote(dao, "athena", "bad")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_recency(
        reference_time=datetime(2026, 8, 21, 12, 0, 0),
    )

    assert results == []


def test_future_recording_time_is_capped_at_maximum_score(
    dao: CollectiveDAO,
    gateway: LiveMemoryGateway,
    source_root: Path,
) -> None:
    create_source_db(
        source_root,
        "athena",
        [
            {
                "id": "future",
                "event_date_precision": "unknown",
                "timestamp": "2026-08-22T12:00:00",
            },
        ],
    )

    entry_id = promote(dao, "athena", "future")

    searcher = TemporalSearcher(dao, gateway)

    results = searcher.search_by_recency(
        reference_time=datetime(2026, 8, 21, 12, 0, 0),
    )

    assert [result.entry_id for result in results] == [entry_id]
    assert results[0].temporal_score == 1.0

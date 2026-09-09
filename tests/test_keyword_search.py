from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.collective import CollectiveDAO
from src.domain.memory_gateway import InMemoryMemoryGateway
from src.retrieval.keyword_index import KeywordIndexer
from src.retrieval.keyword_search import KeywordSearcher


@pytest.fixture
def dao(tmp_path: Path) -> CollectiveDAO:
    dao = CollectiveDAO(
        tmp_path / "collective.db"
    )
    dao.ensure_schema()

    yield dao

    dao.close()


@pytest.fixture
def gateway() -> InMemoryMemoryGateway:
    return InMemoryMemoryGateway()


@pytest.fixture
def retrieval_db(tmp_path: Path) -> Path:
    return tmp_path / "retrieval.db"


@pytest.fixture
def indexer(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    retrieval_db: Path,
) -> KeywordIndexer:
    return KeywordIndexer(
        dao,
        gateway,
        db_path=retrieval_db,
    )


def promote(
    dao: CollectiveDAO,
    profile: str,
    memory_id: str,
) -> int:
    entry_id = dao.insert_collective_entry(
        source_profile=profile,
        origin_memory_id=memory_id,
    )

    dao.update_entry_promoted(entry_id)

    return entry_id


def test_fts5_available(
    indexer: KeywordIndexer,
) -> None:
    indexer.ensure_schema()

    row = indexer.conn.execute(
        "SELECT count(*) FROM memory_fts"
    ).fetchone()

    assert row[0] == 0

    indexer.close()


def test_index_and_search(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_id = promote(
        dao,
        "profileA",
        "memX",
    )

    gateway.add_memory(
        "profileA",
        "memX",
        "machine learning semantic retrieval",
    )

    assert indexer.index_entry(entry_id)

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    results = searcher.search(
        "machine learning"
    )

    assert [r.entry_id for r in results] == [
        entry_id
    ]

    searcher.close()
    indexer.close()


def test_profile_isolation(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_a = promote(
        dao,
        "profileA",
        "memA",
    )

    entry_b = promote(
        dao,
        "profileB",
        "memB",
    )

    gateway.add_memory(
        "profileA",
        "memA",
        "shared retrieval architecture",
    )

    gateway.add_memory(
        "profileB",
        "memB",
        "shared retrieval architecture",
    )

    indexer.index_entry(entry_a)
    indexer.index_entry(entry_b)

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    results = searcher.search(
        "retrieval",
        profile="profileA",
    )

    assert [r.entry_id for r in results] == [
        entry_a
    ]

    searcher.close()
    indexer.close()


def test_revoked_entries_are_not_returned(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_id = promote(
        dao,
        "profileA",
        "memX",
    )

    gateway.add_memory(
        "profileA",
        "memX",
        "revocation test memory",
    )

    indexer.index_entry(entry_id)

    dao.update_entry_revoked(
        entry_id,
        "test revocation",
    )

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    assert searcher.search(
        "revocation"
    ) == []

    searcher.close()
    indexer.close()


def test_unpromoted_entries_are_not_indexed(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_id = dao.insert_collective_entry(
        source_profile="profileA",
        origin_memory_id="memX",
    )

    gateway.add_memory(
        "profileA",
        "memX",
        "unpromoted memory",
    )

    assert indexer.index_entry(entry_id) is False

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    assert searcher.search(
        "unpromoted"
    ) == []

    searcher.close()
    indexer.close()


def test_rebuild(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_a = promote(
        dao,
        "profileA",
        "memA",
    )

    entry_b = promote(
        dao,
        "profileA",
        "memB",
    )

    gateway.add_memory(
        "profileA",
        "memA",
        "alpha retrieval memory",
    )

    gateway.add_memory(
        "profileA",
        "memB",
        "beta retrieval memory",
    )

    result = indexer.rebuild()

    assert result.indexed == 2
    assert result.skipped == 0
    assert result.failed == 0

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    assert [
        r.entry_id
        for r in searcher.search("alpha")
    ] == [entry_a]

    assert [
        r.entry_id
        for r in searcher.search("beta")
    ] == [entry_b]

    searcher.close()
    indexer.close()


def test_deterministic_order(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_a = promote(
        dao,
        "profileA",
        "memA",
    )

    entry_b = promote(
        dao,
        "profileA",
        "memB",
    )

    gateway.add_memory(
        "profileA",
        "memA",
        "shared retrieval term",
    )

    gateway.add_memory(
        "profileA",
        "memB",
        "shared retrieval term",
    )

    indexer.index_entry(entry_a)
    indexer.index_entry(entry_b)

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    ids = [
        r.entry_id
        for r in searcher.search("shared")
    ]

    assert ids == sorted(ids)

    searcher.close()
    indexer.close()


def test_stale_index_entry_is_rejected(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_id = promote(
        dao,
        "profileA",
        "memX",
    )

    gateway.add_memory(
        "profileA",
        "memX",
        "stale lifecycle memory",
    )

    indexer.index_entry(entry_id)

    dao.conn.execute(
        """
        DELETE FROM collective_entries
        WHERE id = ?
        """,
        (entry_id,),
    )
    dao.conn.commit()

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    assert searcher.search(
        "stale lifecycle"
    ) == []

    searcher.close()
    indexer.close()


def test_natural_language_query_with_punctuation(
    dao: CollectiveDAO,
    gateway: InMemoryMemoryGateway,
    indexer: KeywordIndexer,
    retrieval_db: Path,
) -> None:
    entry_id = promote(
        dao,
        "profileA",
        "memX",
    )

    gateway.add_memory(
        "profileA",
        "memX",
        "Phase 7 timeline API was fixed by correcting dependency injection.",
    )

    indexer.index_entry(entry_id)

    searcher = KeywordSearcher(
        dao,
        db_path=retrieval_db,
    )

    results = searcher.search(
        "How did we fix the Phase 7 timeline API?"
    )

    assert [result.entry_id for result in results] == [entry_id]

    searcher.close()
    indexer.close()

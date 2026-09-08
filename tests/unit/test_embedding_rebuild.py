from pathlib import Path

import numpy as np
import pytest

from src.domain.collective import CollectiveDAO
from src.domain.embedding_generator import DEFAULT_DIMENSIONS
from src.domain.memory_gateway import InMemoryMemoryGateway
from src.services.embedding_rebuild import rebuild_embeddings


class FakeEncoder:
    def __init__(self):
        self.calls = []

    def generate(self, sanitized: str) -> bytes:
        self.calls.append(sanitized)

        vector = np.zeros(DEFAULT_DIMENSIONS, dtype=np.float32)
        vector[0] = 1.0

        return vector.tobytes()


class FailingEncoder:
    def generate(self, sanitized: str) -> bytes:
        raise RuntimeError("encoder exploded")


def make_dao(tmp_path: Path) -> CollectiveDAO:
    dao = CollectiveDAO(db_path=tmp_path / "collective.db")
    dao.ensure_schema()
    return dao


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


def get_embedding(dao: CollectiveDAO, entry_id: int):
    row = dao.conn.execute(
        "SELECT embedding FROM collective_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    return row["embedding"]


def test_rebuild_replaces_existing_embeddings(tmp_path):
    dao = make_dao(tmp_path)

    entry_id = dao.add_entry("alice", "mem1")
    promote(dao, entry_id)

    old_embedding = bytes(
        np.full(DEFAULT_DIMENSIONS, 0.25, dtype=np.float32)
    )
    dao.update_entry_embedding(entry_id, old_embedding)

    gateway = InMemoryMemoryGateway(
        {("alice", "mem1"): "new semantic content"}
    )
    encoder = FakeEncoder()

    report = rebuild_embeddings(dao, gateway, encoder)

    assert report.processed == 1
    assert report.updated == 1
    assert report.failures == ()
    assert encoder.calls == ["new semantic content"]

    new_embedding = get_embedding(dao, entry_id)

    assert new_embedding is not None
    assert new_embedding != old_embedding

    vector = np.frombuffer(new_embedding, dtype=np.float32)
    assert vector.shape == (DEFAULT_DIMENSIONS,)
    assert np.isclose(np.linalg.norm(vector), 1.0)


def test_rebuild_processes_only_promoted_non_revoked_entries(tmp_path):
    dao = make_dao(tmp_path)

    promoted_id = dao.add_entry("alice", "mem1")
    unpromoted_id = dao.add_entry("alice", "mem2")
    revoked_id = dao.add_entry("alice", "mem3")

    promote(dao, promoted_id)
    promote(dao, revoked_id)

    dao.conn.execute(
        """
        UPDATE collective_entries
        SET is_revoked = 1
        WHERE id = ?
        """,
        (revoked_id,),
    )
    dao.conn.commit()

    old_unpromoted = b"unpromoted"
    old_revoked = b"revoked"

    dao.update_entry_embedding(unpromoted_id, old_unpromoted)
    dao.update_entry_embedding(revoked_id, old_revoked)

    gateway = InMemoryMemoryGateway(
        {
            ("alice", "mem1"): "promoted",
            ("alice", "mem2"): "unpromoted",
            ("alice", "mem3"): "revoked",
        }
    )
    encoder = FakeEncoder()

    report = rebuild_embeddings(dao, gateway, encoder)

    assert report.processed == 1
    assert report.updated == 1
    assert len(encoder.calls) == 1

    assert get_embedding(dao, unpromoted_id) == old_unpromoted
    assert get_embedding(dao, revoked_id) == old_revoked


def test_missing_memory_rolls_back_all_updates(tmp_path):
    dao = make_dao(tmp_path)

    first_id = dao.add_entry("alice", "mem1")
    second_id = dao.add_entry("alice", "mem2")

    promote(dao, first_id)
    promote(dao, second_id)

    first_old = b"first-old"
    second_old = b"second-old"

    dao.update_entry_embedding(first_id, first_old)
    dao.update_entry_embedding(second_id, second_old)

    gateway = InMemoryMemoryGateway(
        {("alice", "mem1"): "available"}
    )
    encoder = FakeEncoder()

    with pytest.raises(RuntimeError, match="source memory unavailable"):
        rebuild_embeddings(dao, gateway, encoder)

    assert get_embedding(dao, first_id) == first_old
    assert get_embedding(dao, second_id) == second_old


def test_encoder_failure_leaves_database_unchanged(tmp_path):
    dao = make_dao(tmp_path)

    entry_id = dao.add_entry("alice", "mem1")
    promote(dao, entry_id)

    old_embedding = b"original"
    dao.update_entry_embedding(entry_id, old_embedding)

    gateway = InMemoryMemoryGateway(
        {("alice", "mem1"): "content"}
    )

    with pytest.raises(RuntimeError, match="encoder failure"):
        rebuild_embeddings(dao, gateway, FailingEncoder())

    assert get_embedding(dao, entry_id) == old_embedding


def test_rebuild_is_deterministic_in_entry_id_order(tmp_path):
    dao = make_dao(tmp_path)

    first_id = dao.add_entry("alice", "mem1")
    second_id = dao.add_entry("alice", "mem2")

    promote(dao, first_id)
    promote(dao, second_id)

    gateway = InMemoryMemoryGateway(
        {
            ("alice", "mem1"): "first",
            ("alice", "mem2"): "second",
        }
    )
    encoder = FakeEncoder()

    report = rebuild_embeddings(dao, gateway, encoder)

    assert report.processed == 2
    assert report.updated == 2
    assert report.failures == ()
    assert encoder.calls == ["first", "second"]

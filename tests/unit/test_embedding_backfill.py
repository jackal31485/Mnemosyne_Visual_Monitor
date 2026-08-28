import sys, os
# Ensure src is on path for imports used in the test environment.
sys.path.append(os.path.join(os.getcwd(), "src"))

import pytest
from pathlib import Path
import numpy as np

from src.services.embedding_backfill import backfill, _embed_text
from src.domain.collective import CollectiveDAO
from src.domain.memory_gateway import InMemoryMemoryGateway

# Helper to create a temporary database file for DAO.
def make_dao(tmp_path: Path) -> CollectiveDAO:
    db_file = tmp_path / "collective.db"
    dao = CollectiveDAO(db_path=db_file)
    dao.ensure_schema()
    return dao

@pytest.fixture
def dao(tmp_path):
    return make_dao(tmp_path)

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

def test_successful_backfill(dao: CollectiveDAO):
    gw = InMemoryMemoryGateway({("alice", "mem1"): "Hello world"})
    entry_id = dao.add_entry("alice", "mem1")

    failures = backfill(dao, gw)
    assert failures == []

    cur = dao.conn.execute(
        "SELECT embedding FROM collective_entries WHERE id = ?",
        (entry_id,),
    )
    emb_bytes = cur.fetchone()["embedding"]
    assert emb_bytes is not None and len(emb_bytes) == 1536
    vec = np.frombuffer(emb_bytes, dtype=np.float32)
    assert vec.size == 384


def test_already_embedded_ignored(dao: CollectiveDAO):
    gw = InMemoryMemoryGateway({("bob", "mem2"): "foo bar baz"})
    entry_id = dao.add_entry("bob", "mem2")

    existing_bytes = _embed_text("foo bar baz")
    dao.update_entry_embedding(entry_id, existing_bytes)

    failures = backfill(dao, gw)
    assert failures == []

    cur = dao.conn.execute(
        "SELECT embedding FROM collective_entries WHERE id = ?",
        (entry_id,),
    )
    emb_bytes = cur.fetchone()["embedding"]
    assert emb_bytes == existing_bytes


def test_missing_memory_skipped(dao: CollectiveDAO):
    gw = InMemoryMemoryGateway({})
    entry_id = dao.add_entry("charlie", "mem3")

    failures = backfill(dao, gw)
    assert len(failures) == 1
    f_entry_id, prof, memid = failures[0]
    assert f_entry_id == entry_id and prof == "charlie" and memid == "mem3"

    cur = dao.conn.execute(
        "SELECT embedding FROM collective_entries WHERE id = ?",
        (entry_id,),
    )
    emb_bytes = cur.fetchone()["embedding"]
    assert emb_bytes is None or emb_bytes == b''


def test_partial_processing_restartable(dao: CollectiveDAO):
    gw = InMemoryMemoryGateway({("dave", "mem4"): "alpha", ("eve", "mem5"): "beta"})

    id4 = dao.add_entry("dave", "mem4")
    id5 = dao.add_entry("eve", "mem5")

    dao.update_entry_embedding(id4, _embed_text("alpha"))

    failures = backfill(dao, gw)
    assert failures == []
    for eid in (id4, id5):
        row = dao.conn.execute(
            "SELECT embedding FROM collective_entries WHERE id = ?",
            (eid,),
        ).fetchone()
        assert row["embedding"] is not None
        assert len(row["embedding"]) == 1536

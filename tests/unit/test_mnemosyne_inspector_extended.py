import pytest
from pathlib import Path
import sqlite3
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot

# helper: create simple db with optional vector and index

def _create_db(tmp_path: Path, *, with_vec=False, idx=True) -> Path:
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE foo(id INTEGER PRIMARY KEY, val TEXT)")
    for i in range(3):
        cur.execute("INSERT INTO foo(val) VALUES (?)", (f"row{i}",))
    if idx:
        cur.execute("CREATE INDEX ix_val ON foo(val)")
    if with_vec:
        # try virtual, fallback to normal
        try:
            cur.execute("CREATE VIRTUAL TABLE vec_tbl USING vec0(data BLOB)")
        except Exception:
            cur.execute("CREATE TABLE vec_tbl(id INTEGER PRIMARY KEY, data BLOB)")
    conn.commit(); conn.close()
    return db


def test_table_and_index_metadata(tmp_path: Path):
    db = _create_db(tmp_path, with_vec=False, idx=True)
    snap = inspect_sqlite_database(str(db), enable_vectors=False)
    assert isinstance(snap, SchemaSnapshot)
    foo = next(t for t in snap.tables if t.name == "foo")
    assert set(foo.columns) == {"id", "val"}
    assert foo.row_count == 3
    # index should be present
    idx_names = [i.name for i in snap.indexes]
    assert any(n.lower() == "ix_val" or n.lower().startswith("idx_foo") for n in idx_names)

# vector/table detection already tested, but verify enable_vectors True gracefully fails when extension missing
def test_enable_vectors_graceful_fail(tmp_path: Path):
    db = _create_db(tmp_path, with_vec=True)
    # No sqlite_vec extension; calling with vectors should raise RuntimeError
    with pytest.raises(RuntimeError) as e_info:
        inspect_sqlite_database(str(db), enable_vectors=True)
    assert "Failed to load sqlite_vec" in str(e_info.value)

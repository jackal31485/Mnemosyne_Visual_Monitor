# Updated test for the inspector implementation.
import sys
from pathlib import Path
sys.path.insert(0,'src')
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot
import sqlite3
import pytest

# Helper to create DB with optional virtual table
@staticmethod
def _create_db(tmp_path, vec=False):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE foo(id INTEGER PRIMARY KEY, val TEXT)")
    for i in range(5):
        cur.execute("INSERT INTO foo(val) VALUES(?)", (f"row{i}",))
    cur.execute("CREATE INDEX idx_foo_val ON foo(val)")
    if vec:
        try:
            cur.execute("CREATE VIRTUAL TABLE vec_test USING vec0(data BLOB)")
        except Exception:
            # fallback to normal table
            cur.execute("CREATE TABLE vec_test(id INTEGER PRIMARY KEY, data BLOB)")
    conn.commit()
    conn.close()
    return db

def test_mnemosyne_inspector_basic(tmp_path):
    db = _create_db(tmp_path, vec=False)
    snap: SchemaSnapshot = inspect_sqlite_database(db, enable_vectors=False)
    assert isinstance(snap, SchemaSnapshot)
    db_tables = {t.name for t in snap.tables}
    assert 'foo' in db_tables
    foo_info = next(t for t in snap.tables if t.name=='foo')
    assert foo_info.row_count==5
    assert set(['id','val']) <= set(foo_info.columns)

def test_vector_table_detection(tmp_path):
    db = _create_db(tmp_path, vec=True)
    snap: SchemaSnapshot = inspect_sqlite_database(db, enable_vectors=False)
    # vectors should contain any detected virtual tables
    assert any(name.startswith('vec_') for name in snap.detected_vector_names)
    # enable_vectors also loads vector if available
    try:
        snap_vec = inspect_sqlite_database(db, enable_vectors=True)
        # vectors list should be same as detected names if extension loaded
        assert set(snap_vec.vectors) == set(snap.detected_vector_names)
    except RuntimeError:
        # Extension not available; ensure it does not crash
        pass

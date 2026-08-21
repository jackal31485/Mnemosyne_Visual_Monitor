import pytest
import tempfile
import os
import sqlite3
from pathlib import Path
from discovery.mnemosyne_inspector import inspect_sqlite_database

def temp_db_with_vec_table(with_vec: bool):
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    conn = sqlite3.connect(str(db_path))
    if with_vec:
        # attempt to create a vector table – ignore failure
        try:
            import sqlite_vec  # type: ignore
            sqlite_vec.load(conn)  # pragma: no cover - we may not have it
        except Exception:
            pass
        conn.execute("CREATE VIRTUAL TABLE vec_tbl USING vec0('col1 TEXT')")
    else:
        conn.execute("CREATE TABLE vec_tbl(col1 TEXT)")
    conn.commit()
    conn.close()
    return Path(db_path)

def test_disable_vector_support():
    db = temp_db_with_vec_table(False)
    res = inspect_sqlite_database(db, enable_vectors=False)
    assert not res.vector_support_enabled
    assert "vec_tbl" in res.detected_vector_names
    assert res.vectors == res.detected_vector_names

# Verify that enabling vectors without actual extension raises RuntimeError when sqlite3 cannot load extensions.

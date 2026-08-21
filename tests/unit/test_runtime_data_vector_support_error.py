import pytest
from pathlib import Path
import sqlite3
from discovery.mnemosyne_inspector import inspect_sqlite_database

def test_enable_vector_support_raises(tmp_path: Path):
    # Create a simple SQLite database without vector tables
    db = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db))
    conn.close()
    try:
        inspect_sqlite_database(db, enable_vectors=True)
    except RuntimeError as e:
        assert "Failed to load sqlite_vec" in str(e)
    else:
        pytest.fail("Expected RuntimeError when vectors enabled without extension")

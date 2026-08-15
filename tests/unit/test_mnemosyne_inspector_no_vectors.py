import pytest
from pathlib import Path
import sqlite3
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot

# Helper fixture for db without any vec_ tables
def create_db_no_vec(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE foo(id INTEGER PRIMARY KEY, val TEXT)")
    for i in range(3):
        cur.execute("INSERT INTO foo(val) VALUES(?)", (f"row{i}",))
    conn.commit()
    conn.close()
    return db

@pytest.mark.parametrize("enable_vectors", [False, True])
def test_vector_detection_no_vec_tables(tmp_path: Path, enable_vectors: bool):
    db = create_db_no_vec(tmp_path)
    try:
        snap: SchemaSnapshot = inspect_sqlite_database(db, enable_vectors=enable_vectors)
    except RuntimeError as e:
        # If extension not available when enable=True, skip test.
        pytest.skip(f"sqlite_vec not available: {e}")
    assert isinstance(snap, SchemaSnapshot)
    # No vec_ tables should be detected
    assert snap.detected_vector_names == []
    assert snap.vectors == []

import pytest
import sys
from pathlib import Path
import sqlite3
# Ensure src is on sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot

# Helper to create a db with a simple table

def make_db(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE foo(id INTEGER PRIMARY KEY, val TEXT)")
    cur.execute("INSERT INTO foo(val) VALUES(?)", ("init",))
    conn.commit(); conn.close()

@pytest.fixture
def db_a(tmp_path: Path):
    path = tmp_path / "dbA.sqlite"
    make_db(path)
    return path

@pytest.fixture
def db_b(tmp_path: Path):
    path = tmp_path / "dbB.sqlite"
    make_db(path)
    return path

# Profile isolation test – modifying one DB must not touch the other.
def test_profile_isolation(db_a, db_b):
    # Count before
    conn_a = sqlite3.connect(str(db_a))
    cnt_a1 = conn_a.execute("SELECT COUNT(*) FROM foo").fetchone()[0]
    conn_a.close()
    conn_b = sqlite3.connect(str(db_b))
    cnt_b1 = conn_b.execute("SELECT COUNT(*) FROM foo").fetchone()[0]
    conn_b.close()

    # Insert into dbA
    conn_a = sqlite3.connect(str(db_a))
    conn_a.execute("INSERT INTO foo(val) VALUES(?)", ("extra",))
    conn_a.commit(); conn_a.close()

    cnt_a2 = sqlite3.connect(str(db_a)).execute("SELECT COUNT(*) FROM foo").fetchone()[0]
    cnt_b2 = sqlite3.connect(str(db_b)).execute("SELECT COUNT(*) FROM foo").fetchone()[0]

    assert cnt_a2 == cnt_a1 + 1
    assert cnt_b2 == cnt_b1

# Test missing database handling.
def test_inspect_missing_db(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.sqlite"
    with pytest.raises(FileNotFoundError):
        inspect_sqlite_database(str(non_existent))

# Test WAL/SHM detection (already covered) – just ensure function returns flags.
def test_wal_shm_detection(db_a, tmp_path: Path):
    conn = sqlite3.connect(str(db_a))
    conn.close()
    wal_file = db_a.with_name(db_a.name + ".wal") if not db_a.suffix else db_a.with_name(db_a.stem + db_a.suffix + ".wal")
    shm_file = db_a.with_name(db_a.name + "-shm") if not db_a.suffix else db_a.with_name(db_a.stem + db_a.suffix + "-shm")
    wal_file.write_text("dummy WAL data")
    shm_file.write_text("dummy SHM data")
    snap = inspect_sqlite_database(str(db_a), enable_vectors=False)
    assert snap.wal_present
    assert snap.shm_present

# Test sqlite_vec detection – expect vector_support_enabled to be False if extension unavailable.
def test_sqlite_vec_detection(db_a):
    # The behaviour depends on whether the optional sqlite_vec extension is available.
    try:
        snap = inspect_sqlite_database(str(db_a), enable_vectors=True)
    except RuntimeError as exc:  # Extension not present
        assert "Failed to load sqlite_vec" in str(exc)
        return

    # If we reached here, the extension was loaded successfully.
    assert snap.vector_support_enabled is True
    assert len(snap.vectors) > 0

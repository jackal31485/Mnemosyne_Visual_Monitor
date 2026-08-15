import pytest
import sqlite3
from pathlib import Path
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot

@pytest.fixture()
def sqlite_db(tmp_path: Path) -> Path:
    # create a minimal db file
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE foo(id INTEGER PRIMARY KEY, val TEXT)")
    cur.execute("INSERT INTO foo(val) VALUES(? )", ("row0",))
    conn.commit(); conn.close()
    return db

def test_wal_shm_presence_default(sqlite_db: Path):
    snap = inspect_sqlite_database(str(sqlite_db), enable_vectors=False)
    assert not snap.wal_present, "Default DB should not have .wal"
    assert not snap.shm_present, "Default DB should not have -shm"

def test_wal_shm_detection(tmp_path: Path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("CREATE TABLE foo(id INTEGER PRIMARY KEY, val TEXT)")
    conn.commit(); conn.close()

    wal_file = db.with_name(db.name + ".wal") if not db.suffix else db.with_name(db.stem + db.suffix + ".wal")
    shm_file = db.with_name(db.name + "-shm") if not db.suffix else db.with_name(db.stem + db.suffix + "-shm")
    # create dummy files
    wal_file.write_text("dummy WAL data")
    shm_file.write_text("dummy SHM data")

    snap = inspect_sqlite_database(str(db), enable_vectors=False)
    assert snap.wal_present, ".wal file should be detected"
    assert snap.shm_present, "-shm file should be detected"

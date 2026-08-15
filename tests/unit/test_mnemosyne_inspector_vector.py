import pytest
from pathlib import Path
import sqlite3
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot, TableInfo, IndexInfo

def create_temp_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE normal (id INTEGER PRIMARY KEY, val TEXT)")
    cur.execute("CREATE VIRTUAL TABLE vec_test USING vec0(data BLOB)")
    conn.commit()
    conn.close()
    return db

@pytest.fixture
def db(tmp_path):
    return create_temp_db(tmp_path)

# tests to be added

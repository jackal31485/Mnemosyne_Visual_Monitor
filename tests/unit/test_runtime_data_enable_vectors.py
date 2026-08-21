import pytest
import tempfile
import os
from pathlib import Path
import sqlite3

from discovery.runtime_data import get_runtime_data, RuntimeData

# Helper: create an empty SQLite database (no tables)

def make_empty_sqlite() -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
    path = Path(tmp.name)
    # Create a connection to ensure file exists
    conn = sqlite3.connect(str(path))
    conn.close()
    return path


def test_runtime_data_enable_vectors_false():
    """When enable_vectors is False, the schema should have vector_support_enabled==False.
    The inspector may still detect existing vector tables but should not attempt to load sqlite_vec extension.
    """
    db_path = make_empty_sqlite()
    try:
        rd = get_runtime_data(db_path, enable_vectors=False)
        assert isinstance(rd, RuntimeData)
        # Schema should be present (since we passed a path), but with no vector support
        schema = rd.mnemosyne_schema
        assert schema is not None
        assert schema.vector_support_enabled is False
    finally:
        os.remove(db_path)

# tests for runtime_data
import os
import tempfile
import sqlite3
from pathlib import Path
import pytest

from discovery.runtime_data import get_runtime_data, RuntimeData

# Helper: empty SQLite database
def _make_empty_db() -> Path:
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    conn = sqlite3.connect(str(path))
    conn.close()
    return Path(path)


def test_get_runtime_data_no_path():
    rd = get_runtime_data()
    assert isinstance(rd, RuntimeData)
    assert rd.mnemosyne_schema is None


def test_get_runtime_data_default_vectors_behavior(tmp_path: Path):
    db = _make_empty_db()
    try:
        rd = get_runtime_data(db)
        assert isinstance(rd, RuntimeData)
    except RuntimeError:
        pass
    finally:
        os.remove(str(db))


def test_get_runtime_data_disable_vectors(tmp_path: Path):
    db = _make_empty_db()
    try:
        rd = get_runtime_data(db, enable_vectors=False)
        assert isinstance(rd, RuntimeData)
        schema = rd.mnemosyne_schema
        assert schema is not None
        assert schema.vector_support_enabled is False
    finally:
        os.remove(str(db))


def test_get_runtime_data_invalid_path():
    invalid = Path('file_does_not_exist.db')
    with pytest.raises(FileNotFoundError):
        get_runtime_data(invalid)

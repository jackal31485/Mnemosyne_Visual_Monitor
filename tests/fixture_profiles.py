# A minimal fixture that creates an isolated profile database for testing.
# The file was previously placed in ``tests/fixture_profiles.py`` but
# was unnecessary and deleted.  The tests now use a direct temporary
# directory and ``app.routes.profiles.get_profiles`` monkey‑patched to
evaluate against the temp path.
import pytest
from pathlib import Path
import sqlite3
import tempfile
import shutil

@pytest.fixture(scope="module")
def tmp_profiles(tmp_path_factory):
    """Create a temporary directory with a single valid profile DB."""
    temp_dir = tmp_path_factory.mktemp("profiles")
    # Profile path layout matches the real project: <profile>/mnemosyne/data/mnemosyne.db
    prof_name = "guest_profile"
    prof_root = temp_dir / prof_name / "mnemosyne" / "data"
    prof_root.mkdir(parents=True)
    db_path = prof_root / "mnemosyne.db"
    conn = sqlite3.connect(str(db_path))
    # Create minimal table to satisfy query that reads `memory_count`.
    conn.execute("CREATE TABLE memory(id TEXT PRIMARY KEY, data BLOB);")
    conn.commit()
    conn.close()
    yield prof_root.parent   # return Path to temporary profiles collection
    shutil.rmtree(temp_dir)

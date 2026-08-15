# Keep the integration test as is but use relative import via sys.path during runtime.
import pytest
from pathlib import Path
import sys, shutil, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from discovery.mnemosyne_inspector import inspect_sqlite_database, SchemaSnapshot

ATHENA_DB = Path.home() / "mnemosyne.db"
@pytest.mark.skipif(not ATHENA_DB.is_file(), reason="Athena database not present in test environment")
def test_integration_with_real_athena(tmp_path):
    tmp_db = tmp_path / "mnemosyne.db"
    shutil.copy2(str(ATHENA_DB), str(tmp_db))
    snap: SchemaSnapshot = inspect_sqlite_database(tmp_db, enable_vectors=True)
    assert isinstance(snap, SchemaSnapshot)
    assert snap.sqlite_version.startswith("3.")
    table_names = [t.name for t in snap.tables]
    if "vec_episodes" not in table_names:
        assert len(table_names) > 0

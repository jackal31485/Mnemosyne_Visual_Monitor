from app.routes.profiles import get_profiles
import pytest

def test_discover_all_profiles():
    profiles = get_profiles()
    assert len(profiles) >= 1
    ids = {p.id for p in profiles}
    assert 'athena' in ids
    assert all(p.memory_count is not None for p in profiles)

def test_missing_db_skipped(tmp_path):
    import pathlib, tempfile, shutil
    tmpdir = tempfile.mkdtemp()
    try:
        from app.routes.profiles import _discover_profile
        path_without_db = pathlib.Path(tmpdir)
        assert _discover_profile(path_without_db) is None
    finally:
        shutil.rmtree(tmpdir)

@pytest.mark.skip(reason='Duplicate detection not yet coded')
def test_duplicate_db_detection():
    pass

import os
from pathlib import Path
from typing import List

from ..schemas import ProfileDTO

# Helper: find databases for a single profile directory

def _discover_mnemosyne_db(profile_dir: Path) -> Path | None:
    """Return path to the Mnemosyne SQLite database for *profile_dir*.
    The expected location is
   ~/.hermes/profiles/<profile>/mnemosyne/data/mnemosyne.db.
    If the file does not exist or cannot be accessed, return ``None``.
    """
    db_path = profile_dir / "mnemosyne" / "data" / "mnemosyne.db"
    if db_path.is_file():
        return db_path.resolve()
    return None

# Backward-compatible discovery helper used by existing tests/callers.
def _discover_profile(profile_dir: Path) -> Path | None:
    """Return the discovered Mnemosyne database for a Hermes profile."""
    return _discover_mnemosyne_db(profile_dir)


# Helper: count rows in the Mnemosyne working-memory table

def _count_working_memory(db_path: str) -> int:
    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM working_memory")
        return cur.fetchone()[0]
    except Exception:  # pragma: no cover – if table missing simply return 0
        return 0

from fastapi import APIRouter

router = APIRouter()

@router.get("/api/profiles", response_model=List[ProfileDTO])
def get_profiles() -> List[ProfileDTO]:
    profiles: List[ProfileDTO] = []
    base_path = Path.home() / ".hermes" / "profiles"
    if not base_path.is_dir():
        return profiles
    for profile_dir in sorted(p for p in base_path.iterdir() if p.is_dir()):
        db_obj = _discover_mnemosyne_db(profile_dir)
        if not db_obj:
            continue  # skip profiles without a Mnemosyne database
        memory_count = _count_working_memory(str(db_obj))
        profiles.append(
            ProfileDTO(id=profile_dir.name.lower(), name=profile_dir.name.title(), memory_count=int(memory_count))
        )
    return profiles

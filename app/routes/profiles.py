import os
from pathlib import Path
from typing import List

from ..schemas import ProfileDTO

# Helper: find databases for a single profile directory

def _discover_profile(profile_path: Path) -> str | None:
    """Return first SQLite file path found under *profile_path*.
    Searches the directory and, if none found, searches one level deeper.
    Returns ``None`` if no db discovered.
    """
    for entry in profile_path.iterdir():
        if entry.is_file() and entry.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            return str(entry.resolve())
    # search one level deeper just in case the database is nested
    try:
        for child in profile_path.rglob("*"):
            if child.is_file() and child.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                return str(child.resolve())
    except Exception:
        pass
    return None

# Helper: try to count rows in a known table (nodes)

def _count_nodes(db_path: str) -> int:
    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes")
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
        db = _discover_profile(profile_dir)
        if not db:
            continue  # skip profiles without a database discovery
        memory_count = _count_nodes(db)
        profiles.append(
            ProfileDTO(id=profile_dir.name.lower(), name=profile_dir.name.title(), memory_count=int(memory_count))
        )
    return profiles

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .collective import DB_PATH, CollectiveDAO
from .profile_ingest import (
    discover_profile_paths,
    extract_memories,
)


def _rebuild_profile(
    dao: CollectiveDAO,
    profile_dir: Path,
) -> int:
    """
    Rebuild all collective references for one discovered Hermes profile.

    The source Mnemosyne database is opened read-only by extract_memories().
    Only source profile + memory ID are stored in collective.db.
    """

    db_path = (
        profile_dir
        / "mnemosyne"
        / "data"
        / "mnemosyne.db"
    )

    count = 0

    for memory in extract_memories(db_path):
        memory_id = memory.get("id")

        if memory_id is None:
            memory_id = memory.get("memory_id")

        if memory_id is None:
            continue

        memory_id = str(memory_id)

        if not memory_id:
            continue

        dao.insert_collective_entry(
            source_profile=profile_dir.name,
            origin_memory_id=memory_id,
        )

        count += 1

    return count


def nuke_and_rebuild_collective() -> dict[str, Any]:
    """
    Completely rebuild the application collective from every discovered
    Hermes/Mnemosyne profile.

    IMPORTANT:
    - The source Mnemosyne databases are never modified.
    - The existing collective.db remains untouched until the replacement
      database has been built successfully.
    - A successfully built replacement is atomically installed.
    - Every discovered source memory becomes a collective reference.
    - Nothing is promoted automatically.
    """

    profiles = discover_profile_paths()

    live_path = Path(DB_PATH).absolute()
    live_path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_path = tempfile.mkstemp(
        prefix=f".{live_path.name}.",
        suffix=".rebuild",
        dir=live_path.parent,
    )
    os.close(fd)

    temporary_path = Path(temporary_path)
    dao = CollectiveDAO(temporary_path)

    try:
        dao.ensure_schema()

        profile_counts: dict[str, int] = {}
        total = 0

        for profile_dir in sorted(profiles, key=lambda p: p.name.lower()):
            count = _rebuild_profile(
                dao,
                profile_dir,
            )

            profile_counts[profile_dir.name] = count
            total += count

        dao.close()

        # The completed SQLite database is now the replacement candidate.
        # os.replace() provides atomic replacement on the same filesystem.
        os.replace(temporary_path, live_path)

        return {
            "profiles": len(profiles),
            "profile_counts": profile_counts,
            "total_entries": total,
        }

    except Exception:
        dao.close()

        if temporary_path.exists():
            temporary_path.unlink()

        raise

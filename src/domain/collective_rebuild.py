from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .collective import CollectiveDAO
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
    - collective.db is destroyed and recreated.
    - Every discovered source memory becomes a collective reference.
    - Nothing is promoted automatically.
    """

    profiles = discover_profile_paths()

    dao = CollectiveDAO()

    try:
        # Completely destroy the existing application collective.
        dao.reset()

        # Re-open the newly created database and recreate the schema.
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

        return {
            "profiles": len(profiles),
            "profile_counts": profile_counts,
            "total_entries": total,
        }

    finally:
        dao.close()

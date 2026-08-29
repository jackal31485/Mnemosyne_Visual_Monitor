from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from src.domain.profile_ingest import (
    discover_profile_paths,
    extract_memories,
)

router = APIRouter(
    prefix="/api/memories",
    tags=["memories"],
)


@router.get("/inventory")
def memory_inventory():
    """
    Return references to all memories owned by this agent.

    IMPORTANT:
    Raw memory content is never returned.

    The source Mnemosyne databases are opened read-only by
    extract_memories().
    """

    result = {
        "hostname": os.uname().nodename,
        "profiles": [],
    }

    for profile_dir in discover_profile_paths():
        db_path = (
            profile_dir
            / "mnemosyne"
            / "data"
            / "mnemosyne.db"
        )

        profile = {
            "profile": profile_dir.name,
            "memories": [],
        }

        try:
            for memory in extract_memories(db_path):
                memory_id = memory.get("id")

                if memory_id is None:
                    memory_id = memory.get("memory_id")

                if memory_id is None:
                    continue

                profile["memories"].append(
                    {
                        "memory_id": str(memory_id),
                    }
                )

        except Exception as exc:
            profile["error"] = str(exc)

        result["profiles"].append(profile)

    return result
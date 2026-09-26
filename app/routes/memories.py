from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.domain.profile_ingest import (
    discover_profile_paths,
    extract_memories,
)
from src.domain.distributed_memory_gateway import DistributedMemoryGateway

router = APIRouter(
    prefix="/api/memories",
    tags=["memories"],
)


@router.get("/inventory")
def memory_inventory():
    """
    Return references to all memories owned by this agent.

    Raw memory content is never included in the inventory.
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


@router.get("/content")
def memory_content_compatibility():
    """
    Browser API compatibility endpoint.

    The actual source-memory retrieval endpoint remains:
    /api/memories/{profile}/{memory_id}
    """
    return {
        "available": True,
        "endpoint": "/api/memories/{profile}/{memory_id}",
    }


@router.get("/{profile}/{memory_id}")
def get_memory_content(
    profile: str,
    memory_id: str,
):
    """
    Retrieve source memory content for Browser inspection.

    The content is returned transiently and is NEVER stored in
    collective.db.
    """

    gateway = DistributedMemoryGateway()

    try:
        content = gateway.get_memory(
            profile,
            memory_id,
        )
        metadata = gateway.get_memory_metadata(
            profile,
            memory_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "profile": profile,
        "memory_id": memory_id,
        "content": content,
        "event_date": metadata.get("event_date"),
        "event_date_precision": metadata.get(
            "event_date_precision"
        ),
        "timestamp": metadata.get("timestamp"),
        "created_at": metadata.get("created_at"),
    }

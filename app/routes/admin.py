from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.domain.collective import CollectiveDAO
from src.domain.profile_ingest import discover_profile_paths, extract_memories
from src.services.embedding_backfill import backfill
from src.domain.live_memory_gateway import LiveMemoryGateway

router = APIRouter()


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COLLECTIVE_DB = PROJECT_ROOT / "data" / "collective.db"


def _wipe_collective(dao: CollectiveDAO) -> None:
    """
    Completely remove the current collective contents while preserving
    the collective schema.
    """
    dao.conn.execute("DELETE FROM collective_entries")
    dao.conn.commit()


def _rebuild_from_profiles(dao: CollectiveDAO) -> dict:
    """
    Rebuild the collective from the actual Hermes/Mnemosyne profile
    databases discovered on this machine.

    Only source profile + memory ID are copied into the collective.
    Raw memory content never enters the collective database.
    """
    profiles = discover_profile_paths()

    discovered = {}
    total = 0

    for profile_path in profiles:
        profile_name = profile_path.name

        # Locate the profile's Mnemosyne database.
        db_path = (
            profile_path
            / "mnemosyne"
            / "data"
            / "mnemosyne.db"
        )

        if not db_path.is_file():
            continue

        count = 0

        for memory in extract_memories(db_path):
            memory_id = memory["id"]

            # Reference-only collective entry.
            existing = dao.get_by_source(
                profile_name,
                memory_id,
            )

            if existing is None:
                dao.insert_collective_entry(
                    profile_name,
                    memory_id,
                )

            count += 1
            total += 1

        discovered[profile_name] = count

    dao.conn.commit()

    return {
        "memories_discovered": total,
        "profiles_discovered": len(discovered),
        "profiles": discovered,
    }


def _promote_everything(dao: CollectiveDAO) -> int:
    """
    Promote every freshly rebuilt, non-revoked collective entry.

    Nuke & Rebuild is intentionally an administrative rebuild operation:
    the purpose is to reconstruct the complete visible collective rather
    than leave every recovered memory sitting in 'proposed' state.
    """
    rows = dao.conn.execute(
        """
        SELECT id
        FROM collective_entries
        WHERE is_revoked = 0
          AND is_promoted = 0
        ORDER BY id
        """
    ).fetchall()

    promoted = 0

    for row in rows:
        entry_id = row[0]

        dao.conn.execute(
            """
            UPDATE collective_entries
            SET is_promoted = 1
            WHERE id = ?
              AND is_revoked = 0
            """,
            (entry_id,),
        )

        promoted += 1

    dao.conn.commit()

    return promoted


def _collective_counts(dao: CollectiveDAO) -> dict:
    row = dao.conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN is_promoted = 1
                     AND is_revoked = 0
                    THEN 1 ELSE 0
                END
            ) AS promoted,
            SUM(
                CASE
                    WHEN is_promoted = 0
                     AND is_revoked = 0
                    THEN 1 ELSE 0
                END
            ) AS proposed,
            SUM(
                CASE
                    WHEN is_revoked = 1
                    THEN 1 ELSE 0
                END
            ) AS revoked,
            SUM(
                CASE
                    WHEN embedding IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS embedded
        FROM collective_entries
        """
    ).fetchone()

    return {
        "total_entries": row[0] or 0,
        "promoted": row[1] or 0,
        "proposed": row[2] or 0,
        "revoked": row[3] or 0,
        "embedded": row[4] or 0,
    }


def _rebuild_graph() -> dict:
    """
    Rebuild the graph cache/index if the project's GraphService supports
    an explicit rebuild operation.
    """
    try:
        from app.utils import build_graph_service

        service = build_graph_service()

        rebuild = getattr(service, "rebuild", None)

        if callable(rebuild):
            result = rebuild()

            return {
                "rebuilt": True,
                "result": result,
            }

        return {
            "rebuilt": False,
            "reason": "GraphService has no rebuild() method.",
        }

    except Exception as exc:
        return {
            "rebuilt": False,
            "error": str(exc),
        }


@router.post("/api/admin/collective/nuke-rebuild")
def nuke_and_rebuild_everything():
    """
    Administrative full reconstruction.

    Pipeline:

        1. Wipe collective
        2. Discover Hermes profiles
        3. Import reference-only memory IDs
        4. Promote all recovered memories
        5. Rebuild graph
        6. Return complete status

    Raw memory content is never copied into collective.db.
    """
    dao = None

    try:
        dao = CollectiveDAO(COLLECTIVE_DB)
        dao.ensure_schema()

        # ------------------------------------------------------------
        # 1. NUKE
        # ------------------------------------------------------------
        _wipe_collective(dao)

        # ------------------------------------------------------------
        # 2–3. DISCOVER + INGEST
        # ------------------------------------------------------------
        discovery = _rebuild_from_profiles(dao)

        # ------------------------------------------------------------
        # 4. PROMOTE EVERYTHING
        # ------------------------------------------------------------
        promoted = _promote_everything(dao)

        # ------------------------------------------------------------
        # 5. EMBEDDING BACKFILL
        # ------------------------------------------------------------
        #
        # Use the project's existing embedding service.  It reads the
        # source Mnemosyne memories, generates local embeddings, and
        # stores only the embedding vector in collective.db.
        #
        # This must happen AFTER promotion and BEFORE graph rebuild.
        # ------------------------------------------------------------
        gateway = LiveMemoryGateway()
        embedding_failures = backfill(dao, gateway)

        # ------------------------------------------------------------
        # 6. GRAPH REBUILD
        # ------------------------------------------------------------
        graph = _rebuild_graph()

        # ------------------------------------------------------------
        # 6. FINAL COUNTS
        # ------------------------------------------------------------
        collective = _collective_counts(dao)

        return {
            "success": True,
            "message": "Collective rebuilt successfully.",
            "memories_discovered": discovery["memories_discovered"],
            "profiles_discovered": discovery["profiles_discovered"],
            "profiles": discovery["profiles"],
            "promoted_this_run": promoted,
            "embeddings": embedding_failures,
            "collective": collective,
            "graph": graph,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Collective rebuild failed: {exc}",
        )

    finally:
        if dao is not None:
            dao.close()

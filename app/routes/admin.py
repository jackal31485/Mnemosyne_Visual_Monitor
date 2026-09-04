from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
import json

from fastapi import APIRouter, HTTPException

from src.domain.collective import CollectiveDAO
from src.domain.agent_rebuild import (
    AgentEndpoint,
    AgentMemoryClient,
)
from src.services.embedding_backfill import backfill
from src.domain.distributed_memory_gateway import DistributedMemoryGateway
from src.domain.incremental_scan import IncrementalCollectiveScanner
from app.services.discovered_agents import (
    get_discovered_agents,
)

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COLLECTIVE_DB = PROJECT_ROOT / "data" / "collective.db"


def _wipe_collective(dao: CollectiveDAO) -> int:
    """
    Reset Mnemosyne's reconstructed collective and LAN adoption state.

    This removes only Mnemosyne's reconstructed collective data and
    adoption decisions. Source Hermes profiles and memories are never
    modified.
    """

    row = dao.conn.execute(
        "SELECT COUNT(*) FROM collective_entries"
    ).fetchone()

    removed = int(row[0] or 0)

    dao.conn.execute(
        "DELETE FROM collective_entries"
    )
    dao.conn.commit()

    # Nuke also releases all adopted LAN agents. Source agent databases
    # remain completely untouched.
    discovery_db = PROJECT_ROOT / "app" / "db" / "discovery.db"

    with sqlite3.connect(str(discovery_db)) as conn:
        conn.execute(
            """
            UPDATE discovery_records
            SET state = 'DISCOVERED'
            """
        )
        conn.commit()

    return removed


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
    try:
        from app.utils import build_graph_service

        service = build_graph_service()
        rebuild = getattr(
            service,
            "rebuild",
            None,
        )

        if callable(rebuild):
            return {
                "rebuilt": True,
                "result": rebuild(),
            }

        return {
            "rebuilt": False,
            "reason": (
                "GraphService has no rebuild() method."
            ),
        }

    except Exception as exc:
        return {
            "rebuilt": False,
            "error": str(exc),
        }


def _inventory_for_agent(
    agent: AgentEndpoint,
) -> dict:

    client = AgentMemoryClient(agent)

    return client.inventory()


def _import_agent_inventory(
    dao: CollectiveDAO,
    agent: AgentEndpoint,
) -> dict:

    inventory = _inventory_for_agent(agent)

    memories_discovered = 0
    entries_created = 0
    profiles = {}

    for profile in inventory.get(
        "profiles",
        [],
    ):
        profile_name = profile.get("profile")

        if not profile_name:
            continue

        count = 0

        # Namespace source profiles by agent identity.
        # This prevents two agents from having colliding
        # profile/memory IDs.
        source_profile = (
            f"{agent.agent_id}:{profile_name}"
        )

        for memory in profile.get(
            "memories",
            [],
        ):
            memory_id = memory.get(
                "memory_id"
            )

            if memory_id is None:
                continue

            memory_id = str(memory_id)

            existing = dao.get_by_source(
                source_profile,
                memory_id,
            )

            if existing is None:
                dao.insert_collective_entry(
                    source_profile=source_profile,
                    origin_memory_id=memory_id,
                )
                entries_created += 1

            memories_discovered += 1
            count += 1

        profiles[
            source_profile
        ] = count

    return {
        "memories_discovered": memories_discovered,
        "entries_created": entries_created,
        "profiles": profiles,
    }


@router.post("/api/admin/collective/nuke")
def nuke_collective():
    """
    Reset the collective reconstruction and LAN adoption state.

    This does NOT:
      - delete Hermes profiles
      - delete source memories
      - delete agent source databases
      - rebuild anything

    Discovery records are retained but returned to DISCOVERED state.
    """

    dao = None

    try:
        dao = CollectiveDAO(COLLECTIVE_DB)
        dao.ensure_schema()

        removed = _wipe_collective(dao)

        graph = _rebuild_graph()

        from app.routes.discovery import _load_records

        return {
            "success": True,
            "operation": "nuke",
            "entries_removed": removed,
            "collective": _collective_counts(dao),
            "discovery": {
                "agents": _load_records(
                    PROJECT_ROOT / "app" / "db" / "discovery.db",
                    include_stale=False,
                ),
                "scanning": False,
            },
            "graph": graph,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Collective nuke failed: {exc}",
        ) from exc

    finally:
        if dao is not None:
            dao.close()


@router.post("/api/admin/collective/rebuild")
def rebuild_collective():
    """
    Rebuild the collective from ADOPTED LAN agents only.

    This operation does NOT nuke first.
    """

    agents = get_discovered_agents()

    if not agents:
        raise HTTPException(
            status_code=409,
            detail=(
                "No adopted online LAN agents are "
                "available for rebuild."
            ),
        )

    dao = None

    results = []
    total_memories = 0
    total_created = 0

    try:
        dao = CollectiveDAO(COLLECTIVE_DB)
        dao.ensure_schema()

        for agent in agents:
            try:
                result = _import_agent_inventory(
                    dao,
                    agent,
                )

                total_memories += result[
                    "memories_discovered"
                ]

                total_created += result[
                    "entries_created"
                ]

                results.append(
                    {
                        "agent_id": agent.agent_id,
                        "hostname": agent.hostname,
                        "base_url": agent.base_url,
                        "success": True,
                        **result,
                    }
                )

            except Exception as exc:
                results.append(
                    {
                        "agent_id": agent.agent_id,
                        "hostname": agent.hostname,
                        "base_url": agent.base_url,
                        "success": False,
                        "error": str(exc),
                    }
                )

        dao.conn.execute(
            """
            UPDATE collective_entries
            SET is_promoted = 1
            WHERE is_revoked = 0
            """
        )

        dao.conn.commit()

        # Local source memories can still be embedded by the
        # existing gateway when their source_profile is local.
        #
        # Remote agent references are left without embeddings
        # until the remote memory gateway stage is available.
        embedding_failures = []

        try:
            gateway = DistributedMemoryGateway()
            embedding_failures = backfill(
                dao,
                gateway,
            )
        except Exception as exc:
            embedding_failures = [
                ("embedding", "system", str(exc))
            ]

        graph = _rebuild_graph()

        return {
            "success": True,
            "operation": "rebuild",
            "agents": results,
            "agents_discovered": len(agents),
            "memories_discovered": total_memories,
            "entries_created": total_created,
            "embedding_failures": embedding_failures,
            "collective": _collective_counts(dao),
            "graph": graph,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Collective rebuild failed: {exc}",
        ) from exc

    finally:
        if dao is not None:
            dao.close()



@router.post("/api/admin/collective/scan")
def scan_collective():
    """
    Incrementally scan adopted LAN agents for genuinely new memories.

    This operation is strictly non-destructive:
      - existing collective entries are preserved
      - existing embeddings are preserved
      - existing provenance is preserved
      - revoked entries are never deleted
      - LAN adoption state is never changed
      - the graph is rebuilt only when new entries are imported

    A failed agent does not prevent successful agents from being scanned.
    """

    agents = get_discovered_agents()

    if not agents:
        raise HTTPException(
            status_code=409,
            detail=(
                "No adopted online LAN agents are "
                "available for incremental scan."
            ),
        )

    dao = None

    try:
        dao = CollectiveDAO(COLLECTIVE_DB)
        dao.ensure_schema()

        scanner = IncrementalCollectiveScanner(dao)
        result = scanner.scan(agents)

        # Promote only entries created by THIS scan.
        # Existing collective entries are never modified.
        if result.created_entry_ids:
            placeholders = ",".join(
                "?" for _ in result.created_entry_ids
            )
            dao.conn.execute(
                f"""
                UPDATE collective_entries
                SET is_promoted = 1
                WHERE id IN ({placeholders})
                  AND is_revoked = 0
                """,
                result.created_entry_ids,
            )
            dao.conn.commit()

        embedding_failures = []

        if result.created_entry_ids:
            try:
                gateway = DistributedMemoryGateway()
                embedding_failures = backfill(
                    dao,
                    gateway,
                    entry_ids=result.created_entry_ids,
                )
            except Exception as exc:
                embedding_failures = [
                    ("embedding", "system", str(exc))
                ]

        if result.created_entry_ids:
            graph = _rebuild_graph()
        else:
            graph = {
                "rebuilt": False,
                "reason": "No new memories were imported.",
            }

        agent_results = []

        for agent_result in result.agents:
            agent_results.append(
                {
                    "agent_id": agent_result.agent_id,
                    "hostname": agent_result.hostname,
                    "success": agent_result.success,
                    "memories_discovered": (
                        agent_result.memories_discovered
                    ),
                    "already_known": (
                        agent_result.already_known
                    ),
                    "new_memories": (
                        agent_result.new_memories
                    ),
                    "entries_created": (
                        agent_result.entries_created
                    ),
                    "failures": agent_result.failures,
                }
            )

        return {
            "success": True,
            "operation": "scan",
            "agents_scanned": result.agents_scanned,
            "agents_failed": result.agents_failed,
            "memories_discovered": (
                result.memories_discovered
            ),
            "memories_existing": (
                result.memories_existing
            ),
            "memories_new": result.memories_new,
            "entries_created": result.entries_created,
            "embedding_failures": embedding_failures,
            "failures": result.failures,
            "agents": agent_results,
            "collective": _collective_counts(dao),
            "graph": graph,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Collective incremental scan failed: {exc}",
        ) from exc

    finally:
        if dao is not None:
            dao.close()


# Backward compatibility only.
# The old endpoint is deliberately no longer the Browser operation.
@router.post("/api/admin/collective/nuke-rebuild")
def legacy_nuke_rebuild():
    raise HTTPException(
        status_code=410,
        detail=(
            "The combined nuke-rebuild operation has been removed. "
            "Use /api/admin/collective/nuke followed by "
            "/api/admin/collective/rebuild."
        ),
    )

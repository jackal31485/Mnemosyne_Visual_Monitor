from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domain.collective import CollectiveDAO
from domain.live_memory_gateway import LiveMemoryGateway


router = APIRouter()


def collective_dao_dep() -> CollectiveDAO:
    dao = CollectiveDAO()
    dao.ensure_schema()
    return dao


def profile_name(source_profile: str | None) -> str:
    """
    Convert a collective source profile such as:

        UUID:athena

    into the local Hermes profile name:

        athena
    """
    value = str(source_profile or "").strip()

    if ":" in value:
        return value.rsplit(":", 1)[-1]

    return value


def resolve_memory_content(
    gateway: LiveMemoryGateway,
    source_profile: str | None,
    memory_id: str | None,
) -> str | None:
    """
    Resolve source memory content transiently.

    Memory content is never stored in collective.db.
    """
    if not source_profile or not memory_id:
        return None

    profile = profile_name(source_profile)

    if not profile:
        return None

    try:
        return gateway.get_memory(
            profile,
            str(memory_id),
        )
    except (KeyError, FileNotFoundError, ValueError):
        return None
    except Exception:
        # Timeline metadata must remain available even if a source
        # memory is temporarily unavailable.
        return None


def resolve_memory_metadata(
    gateway: LiveMemoryGateway,
    source_profile: str | None,
    memory_id: str | None,
) -> dict[str, object]:
    """Resolve source memory date metadata transiently."""
    if not source_profile or not memory_id:
        return {}

    profile = profile_name(source_profile)

    if not profile:
        return {}

    try:
        return gateway.get_memory_metadata(
            profile,
            str(memory_id),
        )
    except (KeyError, FileNotFoundError, ValueError):
        return {}
    except Exception:
        return {}


@router.get("/api/events")
def get_events(
    profile: Optional[str] = Query(
        None,
        description="Filter events to this source profile",
    ),
    dao: CollectiveDAO = Depends(collective_dao_dep),
):
    if profile:
        rows = dao.conn.execute(
            """
            SELECT
                id,
                source_profile,
                origin_memory_id,
                proposed_at,
                validated_at,
                validator_profile,
                validation_score,
                is_revoked,
                revocation_reason,
                is_promoted
            FROM collective_entries
            WHERE source_profile = ?
               OR source_profile LIKE ?
            ORDER BY id ASC
            """,
            (profile, "%:" + profile),
        ).fetchall()
    else:
        rows = dao.conn.execute(
            """
            SELECT
                id,
                source_profile,
                origin_memory_id,
                proposed_at,
                validated_at,
                validator_profile,
                validation_score,
                is_revoked,
                revocation_reason,
                is_promoted
            FROM collective_entries
            ORDER BY id ASC
            """
        ).fetchall()

    gateway = LiveMemoryGateway()

    events = []

    for row in rows:
        source_profile = row["source_profile"]
        origin_memory_id = row["origin_memory_id"]

        memory_content = resolve_memory_content(
            gateway,
            source_profile,
            origin_memory_id,
        )

        memory_metadata = resolve_memory_metadata(
            gateway,
            source_profile,
            origin_memory_id,
        )

        event_date = memory_metadata.get("event_date")
        timestamp = memory_metadata.get("timestamp")
        created_at = memory_metadata.get("created_at")

        memory_date = (
            event_date
            or timestamp
            or created_at
            or row["proposed_at"]
        )

        events.append(
            {
                "id": row["id"],
                "source_profile": source_profile,
                "profile": profile_name(source_profile),
                "origin_memory_id": origin_memory_id,
                "proposed_at": row["proposed_at"],
                "validated_at": row["validated_at"],
                "validator_profile": row["validator_profile"],
                "validation_score": row["validation_score"],
                "is_revoked": bool(row["is_revoked"]),
                "revocation_reason": row["revocation_reason"],
                "is_promoted": bool(row["is_promoted"]),
                "memory_content": memory_content,
                "event_date": event_date,
                "timestamp": timestamp,
                "created_at": created_at,
                "memory_date": memory_date,
            }
        )

    return {
        "events": events,
    }

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.domain.collective import CollectiveDAO
from src.domain.temporal_historical_summary import (
    TemporalHistoricalSummaryBuilder,
)
from src.services.entity_historical_state_service import (
    EntityHistoricalStateService,
)
from src.services.relationship_historical_state_service import (
    RelationshipHistoricalStateService,
)

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "collective.db"


def _dao() -> CollectiveDAO:
    return CollectiveDAO(DB_PATH)


def _numeric_id(value: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid collective entry id") from exc

    if result < 1:
        raise HTTPException(status_code=400, detail="Invalid collective entry id")

    return result


def _governed_rows(
    dao: CollectiveDAO,
    *,
    source_profile: str | None = None,
) -> list[dict[str, Any]]:
    """
    Read temporal evidence without interpreting historical state in the route.

    The route only assembles the evidence contract needed by the domain services.
    Lifecycle and provenance remain authoritative at the collective layer.
    """
    table_exists = dao.conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'temporal_evidence'
        """
    ).fetchone()

    if table_exists is None:
        return []

    columns = {
        row[1]
        for row in dao.conn.execute(
            "PRAGMA table_info(temporal_evidence)"
        ).fetchall()
    }

    required = {
        "temporal_evidence_id",
        "collective_entry_id",
        "subject_type",
        "subject_id",
        "object_type",
        "object_id",
        "temporal_relation",
        "start_time",
        "end_time",
        "precision",
        "confidence",
        "source_memory_id",
        "source_profile",
    }

    if not required.issubset(columns):
        return []

    rows = dao.conn.execute(
        """
        SELECT
            temporal_evidence_id,
            collective_entry_id,
            subject_type,
            subject_id,
            object_type,
            object_id,
            temporal_relation,
            start_time,
            end_time,
            precision,
            confidence,
            source_memory_id,
            source_profile
        FROM temporal_evidence
        ORDER BY temporal_evidence_id
        """
    ).fetchall()

    governed: list[dict[str, Any]] = []

    for row in rows:
        (
            evidence_id,
            collective_entry_id,
            subject_type,
            subject_id,
            object_type,
            object_id,
            temporal_relation,
            start_time,
            end_time,
            precision,
            confidence,
            source_memory_id,
            evidence_profile,
        ) = row

        if source_profile is not None and evidence_profile != source_profile:
            continue

        lifecycle = dao.get_lifecycle_state(int(collective_entry_id))
        if lifecycle is None:
            continue

        validated_at, is_revoked, _reason, is_promoted = lifecycle

        if validated_at is None or is_revoked or not is_promoted:
            continue

        collective = dao.conn.execute(
            """
            SELECT source_profile, origin_memory_id
            FROM collective_entries
            WHERE id = ?
            """,
            (int(collective_entry_id),),
        ).fetchone()

        if collective is None:
            continue

        collective_profile, origin_memory_id = collective

        if collective_profile != evidence_profile:
            continue

        if str(origin_memory_id) != str(source_memory_id):
            continue

        governed.append(
            {
                "evidence_id": str(evidence_id),
                "collective_entry_id": int(collective_entry_id),
                "subject_type": subject_type,
                "subject_id": str(subject_id),
                "object_type": object_type,
                "object_id": None if object_id is None else str(object_id),
                "relation": temporal_relation,
                "valid_from": start_time,
                "valid_to": end_time,
                "precision": precision,
                "confidence": float(confidence),
                "source_profile": evidence_profile,
                "source_memory_id": str(source_memory_id),
            }
        )

    return governed


def _entity_mappings(
    rows: list[dict[str, Any]],
    entity_id: str,
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []

    for row in rows:
        subject_is_entity = (
            row["subject_type"] == "entity"
            and str(row["subject_id"]) == str(entity_id)
        )
        object_is_entity = (
            row["object_type"] == "entity"
            and str(row["object_id"]) == str(entity_id)
        )

        if not subject_is_entity and not object_is_entity:
            continue

        mappings.append(
            {
                "entity_id": entity_id,
                "state": row["relation"],
                "evidence_id": row["evidence_id"],
                "source_profile": row["source_profile"],
                "source_memory_id": row["source_memory_id"],
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
                "precision": row["precision"],
                "confidence": row["confidence"],
            }
        )

    return mappings


def _entity_history_payload(history: Any) -> dict[str, Any]:
    return {
        "entity_id": history.entity_id,
        "observations": list(history.observations),
        "transitions": list(history.transitions),
        "observation_count": history.observation_count,
        "transition_count": history.transition_count,
        "states": list(history.states),
        "known_timed_observation_count": history.known_timed_observation_count,
        "unknown_timed_observation_count": history.unknown_timed_observation_count,
        "complete": history.complete,
    }


def _relationship_history_payload(history: Any) -> dict[str, Any]:
    return {
        "source_entity_id": history.source_entity_id,
        "target_entity_id": history.target_entity_id,
        "relation": history.relation,
        "observations": list(history.observations),
        "transitions": list(history.transitions),
        "observation_count": history.observation_count,
        "known_timed_observation_count": history.known_timed_observation_count,
        "unknown_timed_observation_count": history.unknown_timed_observation_count,
        "complete": history.complete,
        "observed_active": history.observed_active,
    }


def _entity_summary_payload(summary: Any) -> dict[str, Any]:
    return {
        "entity_id": summary.entity_id,
        "statements": list(summary.statements),
        "observed_states": list(summary.observed_states),
        "observation_count": summary.observation_count,
        "transition_count": summary.transition_count,
        "known_timed_observations": summary.known_timed_observations,
        "unknown_timed_observations": summary.unknown_timed_observations,
        "complete": summary.complete,
        "evidence_count": summary.evidence_count,
    }


def _relationship_summary_payload(summary: Any) -> dict[str, Any]:
    return {
        "source_entity_id": summary.source_entity_id,
        "target_entity_id": summary.target_entity_id,
        "relation": summary.relation,
        "statements": list(summary.statements),
        "observation_count": summary.observation_count,
        "known_timed_observations": summary.known_timed_observations,
        "unknown_timed_observations": summary.unknown_timed_observations,
        "complete": summary.complete,
        "evidence_count": summary.evidence_count,
    }


def _relationship_mappings(
    rows: list[dict[str, Any]],
    source_entity_id: str,
    target_entity_id: str,
    relation: str,
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []

    for row in rows:
        if (
            row["subject_type"] != "entity"
            or row["object_type"] != "entity"
            or str(row["subject_id"]) != str(source_entity_id)
            or str(row["object_id"]) != str(target_entity_id)
            or str(row["relation"]) != str(relation)
        ):
            continue

        mappings.append(
            {
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relation": relation,
                "evidence_id": row["evidence_id"],
                "source_profile": row["source_profile"],
                "source_memory_id": row["source_memory_id"],
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
                "precision": row["precision"],
                "confidence": row["confidence"],
            }
        )

    return mappings


@router.get("/api/temporal/history")
def temporal_history(
    source_profile: str | None = Query(default=None),
) -> dict[str, Any]:
    dao = _dao()

    try:
        rows = _governed_rows(dao, source_profile=source_profile)
    finally:
        dao.close()

    return {
        "count": len(rows),
        "observations": rows,
        "governance": {
            "promoted_only": True,
            "non_revoked_only": True,
            "source_profile_match": True,
            "source_memory_match": True,
        },
    }


@router.get("/api/temporal/history/entity/{entity_id}")
def entity_temporal_history(
    entity_id: str,
    source_profile: str | None = Query(default=None),
) -> dict[str, Any]:
    dao = _dao()

    try:
        rows = _governed_rows(dao, source_profile=source_profile)
    finally:
        dao.close()

    mappings = _entity_mappings(rows, entity_id)

    history = EntityHistoricalStateService.from_mappings(entity_id, mappings)
    summary = TemporalHistoricalSummaryBuilder.entity(history)

    return {
        "entity_id": entity_id,
        "history": _entity_history_payload(history),
        "summary": _entity_summary_payload(summary),
        "governance": {
            "promoted_only": True,
            "non_revoked_only": True,
            "source_profile_match": True,
            "source_memory_match": True,
        },
    }


@router.get("/api/temporal/history/relationship")
def relationship_temporal_history(
    source_entity_id: str,
    target_entity_id: str,
    relation: str,
    source_profile: str | None = Query(default=None),
) -> dict[str, Any]:
    if str(source_entity_id) == str(target_entity_id):
        raise HTTPException(
            status_code=400,
            detail="Relationship history cannot reference the same entity",
        )

    dao = _dao()

    try:
        rows = _governed_rows(dao, source_profile=source_profile)
    finally:
        dao.close()

    mappings = _relationship_mappings(
        rows,
        source_entity_id,
        target_entity_id,
        relation,
    )

    history = RelationshipHistoricalStateService.from_mappings(
        source_entity_id,
        target_entity_id,
        relation,
        mappings,
    )
    summary = TemporalHistoricalSummaryBuilder.relationship(history)

    return {
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "relation": relation,
        "history": _relationship_history_payload(history),
        "summary": _relationship_summary_payload(summary),
        "ended_inferred": False,
        "governance": {
            "promoted_only": True,
            "non_revoked_only": True,
            "source_profile_match": True,
            "source_memory_match": True,
            "missing_evidence_does_not_imply_ended": True,
        },
    }


@router.get("/api/temporal/history/view", response_class=HTMLResponse)
def temporal_history_view() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Mnemosyne Temporal History</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; }
h1 { margin-bottom: .25rem; }
.notice { padding: .8rem; border: 1px solid #ccc; margin: 1rem 0; }
pre { white-space: pre-wrap; word-break: break-word; }
</style>
</head>
<body>
<h1>Temporal History</h1>
<div class="notice">
Temporal history is evidence-backed and governance-filtered.
Missing evidence does not imply that an entity or relationship ended.
</div>
<pre id="output">Loading…</pre>
<script>
fetch('/api/temporal/history')
  .then(response => response.json())
  .then(data => {
    document.getElementById('output').textContent =
      JSON.stringify(data, null, 2);
  })
  .catch(error => {
    document.getElementById('output').textContent =
      'Unable to load temporal history: ' + error;
  });
</script>
</body>
</html>"""


__all__ = ["router"]

"""Phase 14H read-only cross-profile transfer API and Browser surface."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.services.transfer_learning import (
    TransferLearningProjection,
    get_transfer_learning_projection,
)
from src.domain.transfer_contract import TransferRecord
from src.domain.transfer_revocation import RevokedDestinationLearnedState


router = APIRouter(tags=["transfer-learning"])


def _json_value(value: Any) -> Any:
    """Convert domain values to JSON-safe values."""
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, tuple):
        return [_json_value(item) for item in value]

    if isinstance(value, list):
        return [_json_value(item) for item in value]

    if isinstance(value, set | frozenset):
        return sorted(_json_value(item) for item in value)

    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }

    return value


def _transfer_summary(record: TransferRecord) -> dict[str, Any]:
    """Return a safe transfer projection without memory content."""
    provenance = record.provenance

    return {
        "transfer_id": record.transfer_id,
        "candidate_id": record.candidate_id,
        "authorization_id": record.authorization_id,
        "status": record.status.value,
        "version": record.version,
        "created_at": _json_value(record.created_at),
        "adopted_at": _json_value(record.adopted_at),
        "source_profile": provenance.source_profile,
        "destination_profile": provenance.destination_profile,
        "source_knowledge_id": provenance.source_knowledge_id,
        "evidence_ids": list(provenance.evidence_ids),
        "source_memory_ids": list(provenance.source_memory_ids),
        "observation_ids": list(provenance.observation_ids),
        "mental_model_id": provenance.mental_model_id,
        "derivation_method": provenance.derivation_method,
    }


def _revoked_summary(
    state: RevokedDestinationLearnedState,
) -> dict[str, Any]:
    return {
        "learned_id": state.learned_id,
        "transfer_id": state.transfer_id,
        "candidate_id": state.candidate_id,
        "authorization_id": state.authorization_id,
        "source_profile": state.source_profile,
        "destination_profile": state.destination_profile,
        "source_knowledge_id": state.source_knowledge_id,
        "source_memory_ids": list(state.source_memory_ids),
        "observation_ids": list(state.observation_ids),
        "evidence_ids": list(state.evidence_ids),
        "temporal_scope": list(state.temporal_scope),
        "adopted_at": _json_value(state.adopted_at),
        "revoked_at": _json_value(state.revoked_at),
        "version": state.version,
        "status": state.status.value,
        "is_currently_retrievable": state.is_currently_retrievable,
        "revocation_reason": state.revocation_reason.value,
        "derivation_method": state.derivation_method,
    }


def _not_found(transfer_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Transfer not found: {transfer_id}",
    )


@router.get("/api/transfer-learning")
def list_transfer_learning(
    source_profile: str | None = Query(default=None),
    destination_profile: str | None = Query(default=None),
    projection: TransferLearningProjection = Depends(
        get_transfer_learning_projection
    ),
) -> dict[str, Any]:
    records = projection.list_transfers(
        source_profile=source_profile,
        destination_profile=destination_profile,
    )

    return {
        "transfers": [_transfer_summary(record) for record in records],
        "count": len(records),
        "governance": {
            "read_only": True,
            "cross_profile_transfer": True,
            "promoted_only": True,
            "non_revoked_only_for_retrieval": True,
            "raw_memory_content_included": False,
            "implicit_synchronization": False,
        },
    }


@router.get("/api/transfer-learning/{transfer_id}")
def get_transfer_learning(
    transfer_id: str,
    projection: TransferLearningProjection = Depends(
        get_transfer_learning_projection
    ),
) -> dict[str, Any]:
    record = projection.get_transfer(transfer_id)

    if record is None:
        raise _not_found(transfer_id)

    revoked = projection.get_revoked_state(transfer_id)
    revocation = projection.get_revocation(transfer_id)

    return {
        "transfer": _transfer_summary(record),
        "revoked_state": (
            _revoked_summary(revoked)
            if revoked is not None
            else None
        ),
        "revocation": (
            {
                "transfer_id": revocation.transfer_id,
                "candidate_id": revocation.candidate_id,
                "authorization_id": revocation.authorization_id,
                "learned_id": revocation.learned_id,
                "reason": revocation.reason.value,
                "revoked_at": _json_value(revocation.revoked_at),
                "dependency_ids": list(revocation.dependency_ids),
                "rollback": revocation.rollback,
                "derivation_method": revocation.derivation_method,
            }
            if revocation is not None
            else None
        ),
        "governance": {
            "read_only": True,
            "historical_state_preserved": True,
            "retrievable": record.status.value != "revoked",
            "raw_memory_content_included": False,
        },
    }


@router.get("/api/transfer-learning/{transfer_id}/provenance")
def get_transfer_provenance(
    transfer_id: str,
    projection: TransferLearningProjection = Depends(
        get_transfer_learning_projection
    ),
) -> dict[str, Any]:
    record = projection.get_transfer(transfer_id)

    if record is None:
        raise _not_found(transfer_id)

    provenance = record.provenance

    return {
        "transfer_id": transfer_id,
        "provenance": {
            "source_profile": provenance.source_profile,
            "destination_profile": provenance.destination_profile,
            "source_knowledge_id": provenance.source_knowledge_id,
            "transfer_candidate_id": provenance.transfer_candidate_id,
            "transfer_record_id": provenance.transfer_record_id,
            "evidence_ids": list(provenance.evidence_ids),
            "source_memory_ids": list(provenance.source_memory_ids),
            "observation_ids": list(provenance.observation_ids),
            "mental_model_id": provenance.mental_model_id,
            "derivation_method": provenance.derivation_method,
            "raw_memory_content_included": False,
        },
    }


@router.get("/browser/transfer-learning", response_class=HTMLResponse)
def transfer_learning_browser(
    projection: TransferLearningProjection = Depends(
        get_transfer_learning_projection
    ),
) -> HTMLResponse:
    records = projection.list_transfers()

    cards: list[str] = []

    for record in records:
        source = escape(record.provenance.source_profile)
        destination = escape(record.provenance.destination_profile)

        cards.append(
            f"""
            <article class="transfer-card">
                <h2>{escape(record.transfer_id)}</h2>
                <p class="transfer-status">
                    {escape(record.status.value)}
                </p>
                <dl>
                    <dt>Source profile</dt>
                    <dd>{source}</dd>
                    <dt>Destination profile</dt>
                    <dd>{destination}</dd>
                    <dt>Candidate</dt>
                    <dd>{escape(record.candidate_id)}</dd>
                    <dt>Authorization</dt>
                    <dd>{escape(record.authorization_id)}</dd>
                    <dt>Version</dt>
                    <dd>{record.version}</dd>
                </dl>
                <p>
                    <a href="/browser/transfer-learning/{escape(record.transfer_id)}">
                        Inspect transfer governance
                    </a>
                </p>
            </article>
            """
        )

    body = "".join(cards)

    if not body:
        body = """
        <section class="empty-state">
            <h2>No transfer records</h2>
            <p>No Phase 14 cross-profile transfer records are available.</p>
        </section>
        """

    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Mnemosyne Transfer Learning</title>
        <style>
            body {{
                font-family: sans-serif;
                margin: 2rem;
            }}
            .transfer-card {{
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
            }}
            dt {{
                font-weight: bold;
            }}
            dd {{
                margin: 0 0 .5rem 0;
            }}
            .transfer-status {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Mnemosyne Transfer Learning</h1>
        <p>
            Read-only view of governed Phase 14 cross-profile learning.
        </p>
        <p>
            Raw memory content is not included. Historical transfer state
            remains preserved after revocation.
        </p>
        {body}
    </body>
    </html>
    """

    return HTMLResponse(content=html)


@router.get(
    "/browser/transfer-learning/{transfer_id}",
    response_class=HTMLResponse,
)
def transfer_learning_browser_detail(
    transfer_id: str,
    projection: TransferLearningProjection = Depends(
        get_transfer_learning_projection
    ),
) -> HTMLResponse:
    record = projection.get_transfer(transfer_id)

    if record is None:
        raise _not_found(transfer_id)

    provenance = record.provenance
    revoked = projection.get_revoked_state(transfer_id)
    revocation = projection.get_revocation(transfer_id)

    revoked_html = ""

    if revoked is not None:
        revoked_html = f"""
        <section class="revocation">
            <h2>Revocation</h2>
            <p>Status: revoked</p>
            <p>Reason: {escape(revoked.revocation_reason.value)}</p>
            <p>Revoked at: {escape(revoked.revoked_at.isoformat())}</p>
            <p>
                This destination learning is not currently retrievable.
            </p>
        </section>
        """

    revocation_event = ""

    if revocation is not None:
        revocation_event = f"""
        <section>
            <h2>Revocation audit</h2>
            <p>Derivation: {escape(revocation.derivation_method)}</p>
            <p>
                Dependency IDs:
                {escape(", ".join(revocation.dependency_ids) or "none")}
            </p>
            <p>
                Rollback: {escape(str(revocation.rollback))}
            </p>
        </section>
        """

    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Transfer {escape(record.transfer_id)}</title>
    </head>
    <body>
        <h1>Transfer {escape(record.transfer_id)}</h1>

        <dl>
            <dt>Status</dt>
            <dd>{escape(record.status.value)}</dd>
            <dt>Source profile</dt>
            <dd>{escape(provenance.source_profile)}</dd>
            <dt>Destination profile</dt>
            <dd>{escape(provenance.destination_profile)}</dd>
            <dt>Source knowledge</dt>
            <dd>{escape(provenance.source_knowledge_id)}</dd>
            <dt>Candidate</dt>
            <dd>{escape(record.candidate_id)}</dd>
            <dt>Authorization</dt>
            <dd>{escape(record.authorization_id)}</dd>
        </dl>

        <h2>Evidence boundary</h2>
        <p>
            Evidence, observation, memory, and mental-model identifiers are
            retained as provenance. Raw memory content is not included.
        </p>

        <h2>Provenance</h2>
        <p>
            Evidence IDs:
            {escape(", ".join(provenance.evidence_ids))}
        </p>
        <p>
            Observation IDs:
            {escape(", ".join(provenance.observation_ids))}
        </p>
        <p>
            Memory IDs:
            {escape(", ".join(provenance.source_memory_ids))}
        </p>

        {revoked_html}
        {revocation_event}
    </body>
    </html>
    """

    return HTMLResponse(content=html)


__all__ = ["router"]

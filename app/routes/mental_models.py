"""Phase 13G read-only mental-model API and Browser surface."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.services.mental_models import (
    MentalModelProjection,
    get_mental_model_projection,
)
from src.domain.mental_model import MentalModel


router = APIRouter(tags=["mental-models"])


def _json_value(value: Any) -> Any:
    """Convert domain values to JSON-safe values without exposing content."""
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


def _temporal_scope(model: MentalModel) -> Any:
    value = getattr(model, "temporal_scope", None)
    return _json_value(value)


def _summary(model: MentalModel) -> dict[str, Any]:
    """Return the safe current-model projection."""
    return {
        "model_id": model.model_id,
        "model_type": model.model_type.value,
        "title": model.title,
        "description": model.description,
        "entity_ids": list(model.entity_ids),
        "relationship_ids": list(model.relationship_ids),
        "supporting_observation_ids": list(model.supporting_observation_ids),
        "supporting_evidence_ids": list(model.supporting_evidence_ids),
        "supporting_memory_ids": list(model.supporting_memory_ids),
        "source_profiles": list(model.source_profiles),
        "temporal_scope": _temporal_scope(model),
        "confidence": model.confidence,
        "status": model.status.value,
        "version": model.version,
        "created_at": _json_value(model.created_at),
        "updated_at": _json_value(model.updated_at),
        "contradictory_evidence_ids": list(model.contradictory_evidence_ids),
        "derivation_method": model.derivation_method,
        "is_derived": model.is_derived,
    }


def _provenance(model: MentalModel) -> dict[str, Any]:
    provenance = model.provenance

    return {
        "derivation_method": provenance.derivation_method,
        "observation_ids": list(provenance.observation_ids),
        "evidence_ids": list(provenance.evidence_ids),
        "memory_ids": list(provenance.memory_ids),
        "source_profiles": list(provenance.source_profiles),
        "entity_ids": list(provenance.entity_ids),
        "relationship_ids": list(provenance.relationship_ids),
        "raw_memory_content_included": False,
    }


def _not_found(model_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Current mental model not found: {model_id}",
    )


@router.get("/api/mental-models")
def list_mental_models(
    source_profile: str | None = Query(default=None),
    model_type: str | None = Query(default=None),
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> dict[str, Any]:
    models = projection.list_current(
        source_profile=source_profile,
        model_type=model_type,
    )

    return {
        "models": [_summary(model) for model in models],
        "count": len(models),
        "governance": {
            "current_statuses": ["validated", "active"],
            "promoted_only": True,
            "non_revoked_only": True,
            "derived_only": True,
            "raw_memory_content_included": False,
        },
    }


@router.get("/api/mental-models/{model_id}")
def get_mental_model(
    model_id: str,
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> dict[str, Any]:
    model = projection.get_current(model_id)

    if model is None:
        raise _not_found(model_id)

    return {
        "model": _summary(model),
        "governance": {
            "retrievable": True,
            "derived": True,
            "raw_memory_content_included": False,
        },
    }


@router.get("/api/mental-models/{model_id}/provenance")
def get_mental_model_provenance(
    model_id: str,
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> dict[str, Any]:
    model = projection.get_current(model_id)

    if model is None:
        raise _not_found(model_id)

    return {
        "model_id": model.model_id,
        "provenance": _provenance(model),
    }


@router.get("/api/mental-models/{model_id}/evidence")
def get_mental_model_evidence(
    model_id: str,
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> dict[str, Any]:
    model = projection.get_current(model_id)

    if model is None:
        raise _not_found(model_id)

    return {
        "model_id": model.model_id,
        "evidence_ids": list(model.supporting_evidence_ids),
        "contradictory_evidence_ids": list(model.contradictory_evidence_ids),
        "raw_memory_content_included": False,
    }


@router.get("/api/mental-models/{model_id}/observations")
def get_mental_model_observations(
    model_id: str,
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> dict[str, Any]:
    model = projection.get_current(model_id)

    if model is None:
        raise _not_found(model_id)

    return {
        "model_id": model.model_id,
        "observation_ids": list(model.supporting_observation_ids),
    }


@router.get("/browser/mental-models", response_class=HTMLResponse)
def mental_models_browser(
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> HTMLResponse:
    models = projection.list_current()

    cards: list[str] = []

    for model in models:
        cards.append(
            f"""
            <article class="model-card">
                <h2>{escape(model.title)}</h2>
                <p class="model-type">{escape(model.model_type.value)}</p>
                <p>{escape(model.description)}</p>
                <dl>
                    <dt>Status</dt>
                    <dd>{escape(model.status.value)}</dd>
                    <dt>Version</dt>
                    <dd>{model.version}</dd>
                    <dt>Confidence</dt>
                    <dd>{model.confidence:.4f}</dd>
                    <dt>Source profiles</dt>
                    <dd>{escape(", ".join(model.source_profiles))}</dd>
                </dl>
                <p>
                    <a href="/browser/mental-models/{escape(model.model_id)}">
                        Inspect model provenance
                    </a>
                </p>
            </article>
            """
        )

    body = "".join(cards)

    if not body:
        body = """
        <section class="empty-state">
            <h2>No current mental models</h2>
            <p>
                No VALIDATED or ACTIVE mental models are currently exposed
                through the Phase 13G read-only projection.
            </p>
        </section>
        """

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Mnemosyne Mental Models</title>
<style>
body {{
    font-family: system-ui, sans-serif;
    max-width: 1100px;
    margin: 0 auto;
    padding: 32px;
    line-height: 1.5;
}}
header {{
    border-bottom: 1px solid #ccc;
    margin-bottom: 24px;
}}
.model-card {{
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
}}
.model-type {{
    font-size: .85rem;
    text-transform: uppercase;
    letter-spacing: .06em;
}}
.model-card dl {{
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 4px 16px;
}}
.model-card dt {{
    font-weight: 600;
}}
.empty-state {{
    border: 1px dashed #aaa;
    padding: 24px;
}}
.governance {{
    padding: 16px;
    border-left: 4px solid #777;
    margin-bottom: 24px;
}}
</style>
</head>
<body>
<header>
    <h1>Mnemosyne Mental Models</h1>
    <p>Phase 13 derived knowledge — not source memory.</p>
</header>

<section class="governance">
    <strong>Evidence boundary</strong>
    <p>
        This Browser surface exposes only currently retrievable,
        evidence-backed derived models. Source memory content is not
        embedded in the mental-model projection.
    </p>
</section>

{body}
</body>
</html>"""

    return HTMLResponse(content=html)


@router.get("/browser/mental-models/{model_id}", response_class=HTMLResponse)
def mental_model_browser_detail(
    model_id: str,
    projection: MentalModelProjection = Depends(get_mental_model_projection),
) -> HTMLResponse:
    model = projection.get_current(model_id)

    if model is None:
        raise _not_found(model_id)

    evidence = "".join(
        f"<li>{escape(identifier)}</li>"
        for identifier in model.supporting_evidence_ids
    ) or "<li>None</li>"

    observations = "".join(
        f"<li>{escape(identifier)}</li>"
        for identifier in model.supporting_observation_ids
    ) or "<li>None</li>"

    contradictions = "".join(
        f"<li>{escape(identifier)}</li>"
        for identifier in model.contradictory_evidence_ids
    ) or "<li>None</li>"

    memories = "".join(
        f"<li>{escape(identifier)}</li>"
        for identifier in model.supporting_memory_ids
    ) or "<li>None</li>"

    profiles = "".join(
        f"<li>{escape(profile)}</li>"
        for profile in model.source_profiles
    ) or "<li>None</li>"

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(model.title)} — Mnemosyne Mental Model</title>
<style>
body {{
    font-family: system-ui, sans-serif;
    max-width: 1000px;
    margin: 0 auto;
    padding: 32px;
    line-height: 1.5;
}}
section {{
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 20px;
    margin: 16px 0;
}}
dt {{ font-weight: 600; }}
</style>
</head>
<body>
<p><a href="/browser/mental-models">← Mental models</a></p>

<h1>{escape(model.title)}</h1>
<p>{escape(model.description)}</p>

<section>
<h2>Derived model identity</h2>
<dl>
<dt>Model ID</dt><dd>{escape(model.model_id)}</dd>
<dt>Type</dt><dd>{escape(model.model_type.value)}</dd>
<dt>Status</dt><dd>{escape(model.status.value)}</dd>
<dt>Version</dt><dd>{model.version}</dd>
<dt>Confidence</dt><dd>{model.confidence:.4f}</dd>
<dt>Derivation method</dt><dd>{escape(model.derivation_method)}</dd>
</dl>
</section>

<section>
<h2>Supporting evidence</h2>
<ul>{evidence}</ul>
</section>

<section>
<h2>Supporting observations</h2>
<ul>{observations}</ul>
</section>

<section>
<h2>Supporting source memories</h2>
<ul>{memories}</ul>
<p>
    Memory identifiers are shown for provenance only.
    Raw memory content is not included in this mental-model response.
</p>
</section>

<section>
<h2>Source profiles</h2>
<ul>{profiles}</ul>
</section>

<section>
<h2>Contradictory evidence</h2>
<ul>{contradictions}</ul>
</section>

<section>
<h2>Governance</h2>
<p>
    This is a derived mental model. It is not represented as an observed
    source-memory fact. The provenance chain remains inspectable.
</p>
</section>

</body>
</html>"""

    return HTMLResponse(content=html)

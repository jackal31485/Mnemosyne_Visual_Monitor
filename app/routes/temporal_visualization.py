from __future__ import annotations

from html import escape

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.routes.temporal_history import (
    _dao,
    _entity_history_payload,
    _entity_mappings,
    _entity_summary_payload,
    _governed_rows,
    _relationship_history_payload,
    _relationship_mappings,
    _relationship_summary_payload,
)
from src.domain.temporal_historical_summary import (
    TemporalHistoricalSummaryBuilder,
)
from src.services.entity_historical_state_service import EntityHistoricalStateService
from src.services.relationship_historical_state_service import (
    RelationshipHistoricalStateService,
)


router = APIRouter(tags=["temporal-visualization"])


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{
    color-scheme: light dark;
}}
body {{
    font-family: system-ui, sans-serif;
    margin: 0;
    padding: 2rem;
    line-height: 1.45;
}}
main {{
    max-width: 1100px;
    margin: 0 auto;
}}
h1, h2 {{
    margin-top: 0;
}}
.notice {{
    border: 1px solid currentColor;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0 1.5rem;
}}
.timeline {{
    display: grid;
    gap: 1rem;
}}
.observation, .transition {{
    border: 1px solid #888;
    border-radius: 8px;
    padding: 1rem;
}}
.observation {{
    border-left-width: 5px;
}}
.transition {{
    border-left-width: 5px;
}}
.meta {{
    font-size: 0.9rem;
    opacity: 0.8;
}}
.state {{
    font-size: 1.1rem;
    font-weight: 600;
}}
.empty {{
    opacity: 0.7;
    padding: 1rem 0;
}}
dl {{
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.35rem 1rem;
}}
dt {{
    font-weight: 600;
}}
dd {{
    margin: 0;
}}
</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def _value(mapping: dict, *keys: str, default: str = "unknown") -> str:
    for key in keys:
        value = mapping.get(key)
        if value is not None and str(value) != "":
            return str(value)
    return default


def _observation_html(observation: dict, *, relationship: bool = False) -> str:
    if relationship:
        subject = _value(observation, "source_entity_id")
        target = _value(observation, "target_entity_id")
        relation = _value(observation, "relation")
        headline = (
            f"Relationship: {escape(subject)} "
            f"— {escape(relation)} — "
            f"{escape(target)}"
        )
    else:
        state = _value(
            observation,
            "state",
            "state_value",
            "value",
        )
        headline = f"State: {escape(state)}"

    evidence = _value(
        observation,
        "evidence_id",
        "temporal_evidence_id",
    )
    profile = _value(observation, "source_profile")
    memory = _value(observation, "source_memory_id")
    precision = _value(observation, "precision")
    confidence = _value(observation, "confidence")
    valid_from = _value(
        observation,
        "valid_from",
        "start",
    )
    valid_to = _value(
        observation,
        "valid_to",
        "end",
    )

    return f"""
<section class="observation">
<div class="state">{headline}</div>
<dl>
<dt>Valid from</dt><dd>{escape(valid_from)}</dd>
<dt>Valid to</dt><dd>{escape(valid_to)}</dd>
<dt>Precision</dt><dd>{escape(precision)}</dd>
<dt>Confidence</dt><dd>{escape(confidence)}</dd>
<dt>Evidence</dt><dd>{escape(evidence)}</dd>
<dt>Source profile</dt><dd>{escape(profile)}</dd>
<dt>Source memory</dt><dd>{escape(memory)}</dd>
</dl>
</section>
"""


def _transition_html(transition: dict) -> str:
    from_state = _value(transition, "from_state")
    to_state = _value(transition, "to_state")
    evidence_ids = transition.get("evidence_ids", ())

    if isinstance(evidence_ids, (list, tuple)):
        evidence = ", ".join(str(item) for item in evidence_ids)
    else:
        evidence = str(evidence_ids)

    return f"""
<section class="transition">
<div class="state">
Observed transition: {escape(from_state)}
&rarr;
{escape(to_state)}
</div>
<div class="meta">
Evidence: {escape(evidence or "unknown")}
</div>
</section>
"""


def _render_entity(entity_id: str) -> str:
    dao = _dao()
    try:
        rows = _governed_rows(dao)
    finally:
        dao.close()

    mappings = _entity_mappings(rows, entity_id)
    history = EntityHistoricalStateService.from_mappings(
        entity_id,
        mappings,
    )
    summary = TemporalHistoricalSummaryBuilder.entity(history)
    summary_payload = _entity_summary_payload(summary)

    observations = [
        _observation_html(item)
        for item in _entity_history_payload(history)["observations"]
    ]

    transitions = [
        _transition_html(item)
        for item in _entity_history_payload(history)["transitions"]
    ]

    summary_states = summary_payload.get("observed_states", [])
    state_text = ", ".join(str(value) for value in summary_states) or "none"

    body = f"""
<h1>Temporal history — entity {escape(entity_id)}</h1>

<div class="notice">
<strong>Evidence boundary:</strong>
Missing temporal evidence does <strong>not</strong> mean that a state ended.
Gaps in evidence are not interpreted as endings or state changes.
This view is descriptive and only displays governed temporal observations.
</div>

<section>
<h2>Summary</h2>
<dl>
<dt>Observed states</dt><dd>{escape(state_text)}</dd>
<dt>Observations</dt><dd>{escape(str(summary_payload.get("observation_count", 0)))}</dd>
<dt>Transitions</dt><dd>{escape(str(summary_payload.get("transition_count", 0)))}</dd>
<dt>Known timed observations</dt>
<dd>{escape(str(summary_payload.get("known_timed_observations", 0)))}</dd>
<dt>Unknown timed observations</dt>
<dd>{escape(str(summary_payload.get("unknown_timed_observations", 0)))}</dd>
</dl>
</section>

<section>
<h2>Timeline</h2>
<div class="timeline">
{''.join(observations) or '<div class="empty">No governed temporal observations.</div>'}
</div>
</section>

<section>
<h2>Observed transitions</h2>
<div class="timeline">
{''.join(transitions) or '<div class="empty">No observed state transitions.</div>'}
</div>
</section>
"""

    return _page(f"Temporal history — entity {entity_id}", body)


def _render_relationship(
    source_entity_id: str,
    target_entity_id: str,
    relation: str,
) -> str:
    dao = _dao()
    try:
        rows = _governed_rows(dao)
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
    summary_payload = _relationship_summary_payload(summary)
    payload = _relationship_history_payload(history)

    observations = [
        _observation_html(item, relationship=True)
        for item in payload["observations"]
    ]

    body = f"""
<h1>Temporal history — relationship</h1>

<div class="notice">
<strong>Evidence boundary:</strong>
Missing temporal evidence does <strong>not</strong> mean that the
relationship ended. Gaps are not interpreted as relationship endings.
This view is descriptive and only displays governed temporal observations.
</div>

<section>
<h2>Relationship</h2>
<dl>
<dt>Source entity</dt><dd>{escape(source_entity_id)}</dd>
<dt>Target entity</dt><dd>{escape(target_entity_id)}</dd>
<dt>Relation</dt><dd>{escape(relation)}</dd>
</dl>
</section>

<section>
<h2>Summary</h2>
<dl>
<dt>Observations</dt><dd>{escape(str(summary_payload.get("observation_count", 0)))}</dd>
<dt>Known timed observations</dt>
<dd>{escape(str(summary_payload.get("known_timed_observations", 0)))}</dd>
<dt>Unknown timed observations</dt>
<dd>{escape(str(summary_payload.get("unknown_timed_observations", 0)))}</dd>
</dl>
</section>

<section>
<h2>Timeline</h2>
<div class="timeline">
{''.join(observations) or '<div class="empty">No governed temporal observations.</div>'}
</div>
</section>
"""

    return _page("Temporal history — relationship", body)


@router.get(
    "/api/temporal/history/visualization/entity/{entity_id}",
    response_class=HTMLResponse,
)
def entity_temporal_visualization(entity_id: str) -> HTMLResponse:
    return HTMLResponse(_render_entity(entity_id))


@router.get(
    "/api/temporal/history/visualization/relationship",
    response_class=HTMLResponse,
)
def relationship_temporal_visualization(
    source_entity_id: str = Query(...),
    target_entity_id: str = Query(...),
    relation: str = Query(...),
) -> HTMLResponse:
    return HTMLResponse(
        _render_relationship(
            source_entity_id,
            target_entity_id,
            relation,
        )
    )

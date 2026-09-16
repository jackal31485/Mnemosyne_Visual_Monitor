from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.mental_models import router
from app.services.mental_models import MentalModelProjection
from src.domain.mental_model import (
    MentalModel,
    MentalModelProvenance,
    MentalModelStatus,
    MentalModelType,
)


def _model(
    *,
    model_id: str = "model-1",
    status: MentalModelStatus = MentalModelStatus.ACTIVE,
) -> MentalModel:
    now = datetime.now(timezone.utc)

    provenance = MentalModelProvenance(
        derivation_method="phase-13f-evidence-preserving-synthesis",
        observation_ids=("observation-1",),
        evidence_ids=("evidence-1",),
        memory_ids=("memory-1",),
        source_profiles=("profile-a",),
        entity_ids=("entity-1",),
        relationship_ids=("relationship-1",),
    )

    return MentalModel(
        model_id=model_id,
        model_type=MentalModelType.PATTERN,
        title="Validated pattern",
        description="A governed derived pattern.",
        entity_ids=("entity-1",),
        relationship_ids=("relationship-1",),
        supporting_observation_ids=("observation-1",),
        supporting_evidence_ids=("evidence-1",),
        supporting_memory_ids=("memory-1",),
        source_profiles=("profile-a",),
        temporal_scope=("2026-01-01", "2026-12-31"),
        confidence=0.91,
        status=status,
        version=1,
        created_at=now,
        updated_at=now,
        provenance=provenance,
        derivation_method="phase-13f-evidence-preserving-synthesis",
        contradictory_evidence_ids=(),
        staleness_state="current",
    )


def _client(projection: MentalModelProjection) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[
        __import__(
            "app.services.mental_models",
            fromlist=["get_mental_model_projection"],
        ).get_mental_model_projection
    ] = lambda: projection
    return TestClient(application)


def test_list_exposes_current_models_only():
    projection = MentalModelProjection(
        [
            _model(model_id="active", status=MentalModelStatus.ACTIVE),
            _model(model_id="validated", status=MentalModelStatus.VALIDATED),
            _model(model_id="stale", status=MentalModelStatus.STALE),
            _model(model_id="revoked", status=MentalModelStatus.REVOKED),
        ]
    )

    response = _client(projection).get("/api/mental-models")

    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == 2
    assert {item["model_id"] for item in payload["models"]} == {
        "active",
        "validated",
    }
    assert payload["governance"]["promoted_only"] is True
    assert payload["governance"]["non_revoked_only"] is True
    assert payload["governance"]["raw_memory_content_included"] is False


def test_detail_exposes_derived_model_without_raw_memory_content():
    projection = MentalModelProjection([_model()])

    response = _client(projection).get("/api/mental-models/model-1")

    assert response.status_code == 200
    payload = response.json()

    assert payload["model"]["is_derived"] is True
    assert payload["model"]["supporting_memory_ids"] == ["memory-1"]
    assert "content" not in payload["model"]
    assert payload["governance"]["raw_memory_content_included"] is False


def test_provenance_preserves_governed_identifiers():
    projection = MentalModelProjection([_model()])

    response = _client(projection).get(
        "/api/mental-models/model-1/provenance"
    )

    assert response.status_code == 200
    provenance = response.json()["provenance"]

    assert provenance["observation_ids"] == ["observation-1"]
    assert provenance["evidence_ids"] == ["evidence-1"]
    assert provenance["memory_ids"] == ["memory-1"]
    assert provenance["source_profiles"] == ["profile-a"]
    assert provenance["raw_memory_content_included"] is False


def test_evidence_and_observation_views_are_identifier_only():
    projection = MentalModelProjection([_model()])

    client = _client(projection)

    evidence = client.get("/api/mental-models/model-1/evidence")
    observations = client.get("/api/mental-models/model-1/observations")

    assert evidence.status_code == 200
    assert observations.status_code == 200

    assert evidence.json()["evidence_ids"] == ["evidence-1"]
    assert observations.json()["observation_ids"] == ["observation-1"]

    assert "content" not in evidence.json()
    assert "content" not in observations.json()


def test_non_current_model_is_not_retrievable():
    projection = MentalModelProjection(
        [_model(status=MentalModelStatus.SUPERSEDED)]
    )

    response = _client(projection).get("/api/mental-models/model-1")

    assert response.status_code == 404


def test_unknown_model_is_not_found():
    response = _client(MentalModelProjection()).get(
        "/api/mental-models/does-not-exist"
    )

    assert response.status_code == 404


def test_browser_model_list_is_derived_and_governed():
    projection = MentalModelProjection([_model()])

    response = _client(projection).get("/browser/mental-models")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Mnemosyne Mental Models" in response.text
    assert "derived model" in response.text
    assert "Evidence boundary" in response.text
    assert "Validated pattern" in response.text


def test_browser_model_detail_exposes_provenance_without_content():
    projection = MentalModelProjection([_model()])

    response = _client(projection).get(
        "/browser/mental-models/model-1"
    )

    assert response.status_code == 200
    assert "Supporting evidence" in response.text
    assert "observation-1" in response.text
    assert "memory-1" in response.text
    assert "Raw memory content is not included" in response.text


def test_browser_empty_state_is_explicit():
    response = _client(MentalModelProjection()).get(
        "/browser/mental-models"
    )

    assert response.status_code == 200
    assert "No current mental models" in response.text

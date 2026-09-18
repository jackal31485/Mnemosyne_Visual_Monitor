from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.transfer_learning import router
from app.services.transfer_learning import (
    TransferLearningProjection,
    TransferLearningState,
    get_transfer_learning_projection,
)
from src.domain.transfer_contract import (
    TransferAuthorization,
    TransferProvenance,
    TransferRecord,
    TransferStatus,
)
from src.domain.transfer_revocation import (
    RevokedDestinationLearnedState,
    TransferRevocation,
    TransferRevocationReason,
)


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


def _record(
    *,
    transfer_id: str = "transfer-1",
    status: TransferStatus = TransferStatus.AUTHORIZED,
) -> TransferRecord:
    provenance = TransferProvenance(
        source_profile="odin",
        destination_profile="thoth",
        source_knowledge_id="knowledge-1",
        transfer_candidate_id="candidate-1",
        transfer_record_id=transfer_id,
        evidence_ids=("evidence-1",),
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
        mental_model_id=None,
    )

    return TransferRecord(
        transfer_id=transfer_id,
        candidate_id="candidate-1",
        authorization_id="authorization-1",
        provenance=provenance,
        created_at=NOW,
        adopted_at=NOW if status == TransferStatus.ADOPTED else None,
        version=1,
        status=status,
    )


def _authorization() -> TransferAuthorization:
    return TransferAuthorization(
        authorization_id="authorization-1",
        candidate_id="candidate-1",
        source_profile="odin",
        destination_profile="thoth",
        actor="reviewer",
        authorized_at=NOW,
        scope="knowledge-transfer",
        mechanism="human",
    )


def _revoked_state() -> RevokedDestinationLearnedState:
    return RevokedDestinationLearnedState(
        learned_id="learned-1",
        transfer_id="transfer-1",
        candidate_id="candidate-1",
        authorization_id="authorization-1",
        source_profile="odin",
        destination_profile="thoth",
        source_knowledge_id="knowledge-1",
        source_memory_ids=("memory-1",),
        observation_ids=("observation-1",),
        evidence_ids=("evidence-1",),
        temporal_scope=(),
        adopted_at=NOW,
        revoked_at=NOW,
        version=1,
        revocation_reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        derivation_method="phase-14g-transfer-revocation",
    )


def _revocation() -> TransferRevocation:
    return TransferRevocation(
        transfer_id="transfer-1",
        candidate_id="candidate-1",
        authorization_id="authorization-1",
        learned_id="learned-1",
        source_profile="odin",
        destination_profile="thoth",
        reason=TransferRevocationReason.EXPLICIT_ROLLBACK,
        revoked_at=NOW,
        dependency_ids=(),
        rollback=True,
        derivation_method="phase-14g-transfer-revocation",
    )


def _client(
    state: TransferLearningState,
) -> TestClient:
    application = FastAPI()
    application.include_router(router)

    projection = TransferLearningProjection(state)

    application.dependency_overrides[get_transfer_learning_projection] = (
        lambda: projection
    )

    return TestClient(application)


def test_list_transfer_learning_is_read_only_and_governed():
    client = _client(
        TransferLearningState(
            records=(_record(),),
        )
    )

    response = client.get("/api/transfer-learning")

    assert response.status_code == 200
    body = response.json()

    assert body["count"] == 1
    assert body["transfers"][0]["transfer_id"] == "transfer-1"
    assert body["transfers"][0]["source_profile"] == "odin"
    assert body["transfers"][0]["destination_profile"] == "thoth"
    assert body["governance"]["read_only"] is True
    assert body["governance"]["raw_memory_content_included"] is False
    assert body["governance"]["implicit_synchronization"] is False

    assert "raw_memory_content" not in body


def test_list_transfer_learning_filters_by_source_and_destination():
    records = (
        _record(transfer_id="transfer-1"),
        _record(transfer_id="transfer-2"),
    )

    client = _client(
        TransferLearningState(records=records)
    )

    response = client.get(
        "/api/transfer-learning",
        params={
            "source_profile": "odin",
            "destination_profile": "thoth",
        },
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = client.get(
        "/api/transfer-learning",
        params={"source_profile": "athena"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_transfer_detail_includes_revocation_without_memory_content():
    client = _client(
        TransferLearningState(
            records=(
                _record(
                    status=TransferStatus.REVOKED,
                ),
            ),
            revoked_states=(_revoked_state(),),
            revocations=(_revocation(),),
        )
    )

    response = client.get("/api/transfer-learning/transfer-1")

    assert response.status_code == 200
    body = response.json()

    assert body["transfer"]["status"] == "revoked"
    assert body["revoked_state"]["status"] == "revoked"
    assert body["revoked_state"]["is_currently_retrievable"] is False
    assert body["revocation"]["reason"] == "explicit_rollback"
    assert body["revocation"]["rollback"] is True
    assert body["governance"]["historical_state_preserved"] is True
    assert body["governance"]["raw_memory_content_included"] is False

    assert "raw_memory_content" not in body


def test_transfer_detail_missing_returns_404():
    client = _client(TransferLearningState())

    response = client.get("/api/transfer-learning/does-not-exist")

    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


def test_transfer_provenance_exposes_ids_but_not_memory_content():
    client = _client(
        TransferLearningState(
            records=(_record(),),
        )
    )

    response = client.get(
        "/api/transfer-learning/transfer-1/provenance"
    )

    assert response.status_code == 200
    body = response.json()

    provenance = body["provenance"]

    assert provenance["source_profile"] == "odin"
    assert provenance["destination_profile"] == "thoth"
    assert provenance["source_knowledge_id"] == "knowledge-1"
    assert provenance["evidence_ids"] == ["evidence-1"]
    assert provenance["source_memory_ids"] == ["memory-1"]
    assert provenance["observation_ids"] == ["observation-1"]
    assert provenance["raw_memory_content_included"] is False


def test_browser_transfer_learning_is_read_only():
    client = _client(
        TransferLearningState(
            records=(_record(),),
        )
    )

    response = client.get("/browser/transfer-learning")

    assert response.status_code == 200
    assert "Mnemosyne Transfer Learning" in response.text
    assert "transfer-1" in response.text
    assert "odin" in response.text
    assert "thoth" in response.text
    assert "Inspect transfer governance" in response.text


def test_browser_transfer_learning_detail_shows_revocation():
    client = _client(
        TransferLearningState(
            records=(
                _record(status=TransferStatus.REVOKED),
            ),
            revoked_states=(_revoked_state(),),
            revocations=(_revocation(),),
        )
    )

    response = client.get(
        "/browser/transfer-learning/transfer-1"
    )

    assert response.status_code == 200
    assert "Transfer transfer-1" in response.text
    assert "Revocation" in response.text
    assert "explicit_rollback" in response.text
    assert "not currently retrievable" in response.text


def test_browser_transfer_learning_detail_missing_returns_404():
    client = _client(TransferLearningState())

    response = client.get(
        "/browser/transfer-learning/does-not-exist"
    )

    assert response.status_code == 404


def test_transfer_authorization_projection_is_not_exposed_as_raw_object():
    client = _client(
        TransferLearningState(
            records=(_record(),),
            authorizations=(_authorization(),),
        )
    )

    response = client.get("/api/transfer-learning/transfer-1")

    assert response.status_code == 200
    body = response.json()

    assert "authorization" not in body
    assert body["transfer"]["authorization_id"] == "authorization-1"


def teardown_function():
    pass

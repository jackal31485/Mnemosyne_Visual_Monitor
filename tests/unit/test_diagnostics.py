# tests unit/test_diagnostics.py
import time

from src.domain.api import MediationAPI
from src.domain.diagnostics import Diagnostics


def test_basic_health_snapshot():
    api = MediationAPI()
    diag = Diagnostics(api)
    # allow small delay to observe uptime > 0
    time.sleep(0.01)
    snap = diag.health_report()
    assert isinstance(snap, dict)
    assert snap["uptime"] >= 0.01
    assert "queue_depth" in snap
    assert "memory_usage_bytes" in snap
    # Metrics snapshot should match the established Phase 2.4 contract.
    metrics = snap["metrics_snapshot"]
    assert isinstance(metrics, dict)
    assert metrics["total_proposals"] == 0
    assert metrics["state_counts"] == {}
    assert metrics["process_times_ms"] == []


def test_queue_and_memory():
    api = MediationAPI()
    diag = Diagnostics(api)
    # no proposals yet
    assert diag.queue_depth() == 0
    # create a proposal with a valid token by constructing request_json correctly
    auth_token = "user123"
    req = {"source_profile": auth_token, "source_memory_id": "mem1"}
    api.propose(req, auth_token)
    assert diag.queue_depth() == 1
    # memory usage should be > 0 bytes
    assert diag.memory_usage() > 0


def test_metrics_integration():
    api = MediationAPI()
    diag = Diagnostics(api)
    auth_token = "token_a"
    # create and validate to generate metrics counters
    req = {"source_profile": auth_token, "source_memory_id": "memA"}
    status, response = api.propose(req, auth_token)
    assert status == 201
    assert response["state"] == "PROPOSED"

    api.validate(response["proposal_id"])  # triggers state transition and metrics increments

    snap = diag.health_report()
    metrics = snap["metrics_snapshot"]

    assert metrics["total_proposals"] == 1
    assert metrics["state_counts"]["READY_FOR_PROMOTION"] == 1
    assert len(metrics["process_times_ms"]) == 1

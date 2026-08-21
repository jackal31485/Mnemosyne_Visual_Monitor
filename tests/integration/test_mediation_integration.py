import json
import os
from pathlib import Path
import shutil

import pytest

# Import the API and stub classes
from src.domain.api import MediationAPI, SimpleMemoryGateway, SimplePrivacyFilter, SimpleValidator, PrivacyResult, ValidationOutcome
from src.domain.metrics import MetricsCollector

# Helper to create a fresh audit directory
@pytest.fixture
def temp_audit(tmp_path):
    return tmp_path

# Helper to build API with custom components and isolated audit dir
def make_api(gateway=None, validator=None, filter_cls=None, metrics=None, audit_dir=None):
    api = MediationAPI(
        gateway=gateway or SimpleMemoryGateway(),
        validator=validator or SimpleValidator(),
        metrics=metrics or MetricsCollector(),
    )
    # Override filter if provided
    if filter_cls:
        api._filter = filter_cls()
    if audit_dir:
        api.audit_dir = Path(audit_dir)
        api.audit_dir.mkdir(parents=True, exist_ok=True)
    return api

# ---------------------------------------------------------------------------
# 1. Authentication & proposal creation
# ---------------------------------------------------------------------------
def test_auth_token_mismatch(temp_audit):
    api = make_api(audit_dir=temp_audit)
    # token does not match profile in request
    _, resp = api.propose({"source_profile": "alice", "source_memory_id": "mem1"}, auth_token="bob")
    assert resp["error"] == "Unauthorized"

# ---------------------------------------------------------------------------
# 2. Successful flow with proper audit and metrics
# ---------------------------------------------------------------------------
def test_successful_proposal_flow(temp_audit):
    api = make_api(audit_dir=temp_audit)
    status, prop = api.propose({"source_profile": "user", "source_memory_id": "mem123"}, auth_token="user")
    assert status == 201
    pid = prop["proposal_id"]
    # Validate
    v_status, v_resp = api.validate(pid)
    assert v_status == 200 and v_resp["state"] == "READY_FOR_PROMOTION"
    # Audit file exists
    audit_file = Path(temp_audit) / f"{pid}.json"
    assert audit_file.exists()
    audit_content = json.loads(audit_file.read_text())
    assert audit_content["state"] == "READY_FOR_PROMOTION"
    # Metrics
    metrics = api.get_metrics()
    assert metrics["total_proposals"] >= 1
    assert metrics["state_counts"]["PROPOSED"] == 0
    assert metrics["state_counts"]["PRIVACY_FILTERING"] == 0
    assert metrics["state_counts"]["READY_FOR_PROMOTION"] >= 1

# ---------------------------------------------------------------------------
# 3. Privacy rejection path
# ---------------------------------------------------------------------------
def test_privacy_rejection(temp_audit):
    # Memory gateway that returns content containing PII
    class PIIGateway:
        def get_memory(self, profile: str, mem_id: str) -> str:
            return json.dumps({"profile": profile, "id": mem_id, "secret": "PII"})
    # Filter that masks PII
    class MaskingFilter:
        def filter(self, content: str):
            data = json.loads(content)
            if data.get("secret") == "PII":
                masked=["PII"]
                sanitized={k:v for k,v in data.items() if k!="secret"}
                return PrivacyResult(masked_fields=masked, sanitized_content=json.dumps(sanitized))
            return PrivacyResult([], content)
    api = make_api(gateway=PIIGateway(), filter_cls=MaskingFilter, audit_dir=temp_audit)
    status, prop = api.propose({"source_profile": "alice", "source_memory_id": "memX"}, auth_token="alice")
    assert status == 201
    pid = prop["proposal_id"]
    v_status, v_resp = api.validate(pid)
    assert v_status == 422
    assert "PII masked" in v_resp["reason"]
    audit_file = Path(temp_audit) / f"{pid}.json"
    audit_content = json.loads(audit_file.read_text())
    assert audit_content["state"] == "REJECTED"

# ---------------------------------------------------------------------------
# 4. Validator rejection path
# ---------------------------------------------------------------------------
def test_validator_rejection(temp_audit):
    class RejectingValidator:
        def validate(self, data):
            return ValidationOutcome(is_validated=False, reason_for_rejection="Invalid format")
    api = make_api(validator=RejectingValidator(), audit_dir=temp_audit)
    status, prop = api.propose({"source_profile": "bob", "source_memory_id": "memY"}, auth_token="bob")
    assert status == 201
    pid = prop["proposal_id"]
    v_status, v_resp = api.validate(pid)
    assert v_status == 422
    assert v_resp["reason"] == "Invalid format"
    audit_file = Path(temp_audit) / f"{pid}.json"
    audit_content = json.loads(audit_file.read_text())
    assert audit_content["state"] == "REJECTED"

# ---------------------------------------------------------------------------
# 5. Missing proposal handling
# ---------------------------------------------------------------------------
def test_missing_proposal(temp_audit):
    api = make_api(audit_dir=temp_audit)
    status, resp = api.validate("nonexistent-id")
    assert status == 404
    assert "Proposal not found" in resp["error"]

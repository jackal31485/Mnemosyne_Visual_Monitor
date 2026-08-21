import json
from src.domain.api import MediationAPI
from src.domain.metrics import MetricsCollector

class DummyPrivacyResult:
    def __init__(self, masked_fields, sanitized_content):
        self.masked_fields = masked_fields
        self.sanitized_content = sanitized_content

class DummyValidator:
    def __init__(self, accept=True):
        self.accept = accept
    class DummyOutcome:
        def __init__(self, validated: bool, reason=None):
            self.is_validated=validated
            self.reason_for_rejection=reason
    def validate(self, data):
        if not self.accept:
            return DummyValidator.DummyOutcome(False, "Invalid format")
        return DummyValidator.DummyOutcome(True)
class SimpleMemoryGateway:
    def get_memory(self, profile: str, mem_id: str) -> str:
        return json.dumps({"profile": profile, "id": mem_id})

def make_api(gateway=None, validator=None, privacy_filter=None):
    gateway = gateway or SimpleMemoryGateway()
    validator = validator or DummyValidator(True)
    api = MediationAPI(gateway=gateway, validator=validator, metrics=MetricsCollector())
    if privacy_filter:
        api._filter = privacy_filter
    else:
        class SimplePrivacyFilter:
            def filter(self, content: str):
                data = json.loads(content)
                masked = []
                if data.get("secret") == "PII":
                    masked.append("PII")
                sanitized = dict(data)
                if masked:
                    del sanitized["secret"]
                return DummyPrivacyResult(masked, json.dumps(sanitized))
        api._filter = SimplePrivacyFilter()
    return api, api.metrics

# 1. Successful flow

def test_successful_flow():
    api, metrics = make_api()
    req = {"source_profile": "user", "source_memory_id": "mem123"}
    status, prop = api.propose(req, "user")
    assert status == 201
    pid = prop["proposal_id"]
    v_status, v_resp = api.validate(pid)
    assert v_status == 200
    assert v_resp["state"] == "READY_FOR_PROMOTION"
    metrics_snapshot = metrics.get_metrics()
    assert metrics_snapshot["total_proposals"] >= 1
    assert metrics_snapshot["state_counts"]["PROPOSED"] == 0
    assert metrics_snapshot["state_counts"]["READY_FOR_PROMOTION"] > 0

# 2. Privacy rejection when content contains 'PII'

def test_privacy_rejection():
    def pii_gateway():
        class Gate:
            def get_memory(self, profile: str, mem_id: str) -> str:
                return json.dumps({"profile": profile, "id": mem_id, "secret": "PII"})
        return Gate()
    api, _ = make_api(gateway=pii_gateway(), privacy_filter=None)
    req = {"source_profile": "user", "source_memory_id": "mem001"}
    _, prop = api.propose(req, "user")
    pid = prop["proposal_id"]
    status, resp = api.validate(pid)
    assert status == 422
    assert "PII masked" in resp.get("reason","")

# 3. Validator rejection

def test_validator_rejection():
    api, _ = make_api(validator=DummyValidator(False))
    req = {"source_profile": "user", "source_memory_id": "mem002"}
    _, prop = api.propose(req, "user")
    pid = prop["proposal_id"]
    status, resp = api.validate(pid)
    assert status == 422
    assert resp.get("reason") == "Invalid format"

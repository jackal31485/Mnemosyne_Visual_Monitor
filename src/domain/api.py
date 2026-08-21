# src/domain/api.py
"""
Simple, dependency‑free API‑style class for the mediation plane.

It now also records metrics via :class:`~src.domain.metrics.MetricsCollector`.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Minimal stubs for gateway, privacy filter, and validator. These are simple
# stand‑ins so that MediationAPI can be instantiated in the test environment
# without pulling heavy runtime dependencies.
# ---------------------------------------------------------------------------
class SimpleMemoryGateway:
    def get_memory(self, profile: str, mem_id: str) -> str:
        # Return deterministic JSON for testing purposes.
        return f"{{\"profile\": \"{profile}\", \"id\": \"{mem_id}\"}}"

class SimplePrivacyFilter:
    def filter(self, content: str):
        # Pass through the content; no PII is assumed.
        return PrivacyResult(masked_fields=[], sanitized_content=content)

class SimpleValidator:
    def validate(self, data: dict):
        return ValidationOutcome(is_validated=True)

# --- Domain data structures -------------------------------------------------
class PrivacyResult:
    def __init__(self, masked_fields: list[str], sanitized_content: Optional[str] = None):
        self.masked_fields = masked_fields
        self.sanitized_content = sanitized_content

class ValidationOutcome:
    def __init__(self, is_validated: bool, reason_for_rejection: Optional[str] = None):
        self.is_validated = is_validated
        self.reason_for_rejection = reason_for_rejection

# --- Mediation API -------------------------------------------------------
class MediationAPI:
    def __init__(self, gateway=None, validator=None, metrics=None):
        # allow dependency injection for tests
        self._gateway = gateway or SimpleMemoryGateway()
        self._filter = SimplePrivacyFilter()
        self._validator = validator or SimpleValidator()
        self.proposals: Dict[str, dict] = {}
        self.audit_dir = Path("audit")
        self.audit_dir.mkdir(exist_ok=True)
        self.metrics = metrics or MetricsCollector()

    def _write_audit(self, proposal_id: str, state: str, details: dict | None = None):
        data = {"proposal_id": proposal_id, "state": state, "timestamp": datetime.now(timezone.utc).isoformat(),}
        if details:
            data.update(details)
        (self.audit_dir / f"{proposal_id}.json").write_text(json.dumps(data))

    def propose(self, request_json: dict, auth_token: str) -> tuple[int, dict]:
        src = request_json.get("source_profile")
        if src != auth_token:
            return 401, {"error": "Unauthorized"}
        mem_id = request_json.get("source_memory_id")
        if not mem_id or not isinstance(mem_id, str):
            return 400, {"error": "Missing or invalid source_memory_id"}
        proposal_id = str(uuid.uuid4())
        proposal_data: dict = {
            "proposal_id": proposal_id,
            "source_profile": src,
            "source_memory_id": mem_id,
            "state": "PROPOSED",
            "proposed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.proposals[proposal_id] = proposal_data
        self.metrics.proposal_created(proposal_id)
        self._write_audit(proposal_id, "PROPOSED", None)
        return 201, {"proposal_id": proposal_id, "state": "PROPOSED"}

    def validate(self, proposal_id: str) -> tuple[int, dict]:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return 404, {"error": "Proposal not found"}
        # Transition to PRIVACY_FILTERING
        self.metrics.decrement_state(proposal_id, "PROPOSED")
        self.metrics.state_changed(proposal_id, "PRIVACY_FILTERING")
        mem_content = self._gateway.get_memory(proposal["source_profile"], proposal["source_memory_id"])
        pf_result = self._filter.filter(mem_content)
        if pf_result.masked_fields:
            proposal["state"] = "REJECTED"
            self.metrics.decrement_state(proposal_id, "PRIVACY_FILTERING")
            self.metrics.state_changed(proposal_id, "REJECTED")
            self._write_audit(proposal_id, "REJECTED", {"mask": pf_result.masked_fields})
            return 422, {"state": "REJECTED", "reason": f"PII masked: {pf_result.masked_fields}"}
        sanitized = json.loads(pf_result.sanitized_content)
        # Validation step
        val_out = self._validator.validate(sanitized)
        if not val_out.is_validated:
            proposal["state"] = "REJECTED"
            self.metrics.decrement_state(proposal_id, "PRIVACY_FILTERING")
            self.metrics.state_changed(proposal_id, "REJECTED")
            self._write_audit(proposal_id, "REJECTED", {"reason": val_out.reason_for_rejection})
            return 422, {"state": "REJECTED", "reason": val_out.reason_for_rejection}
        # Success
        proposal["state"] = "READY_FOR_PROMOTION"
        self.metrics.decrement_state(proposal_id, "PRIVACY_FILTERING")
        self.metrics.state_changed(proposal_id, "READY_FOR_PROMOTION")
        self.metrics.finished(proposal_id)
        self._write_audit(proposal_id, "READY_FOR_PROMOTION", None)
        return 200, {"proposal_id": proposal_id, "state": "READY_FOR_PROMOTION"}

    def get_metrics(self) -> dict:
        return self.metrics.get_metrics()

__all__ = ["MediationAPI"]

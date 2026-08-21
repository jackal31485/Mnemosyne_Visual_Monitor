# audit_store.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from .models import ProposalState

class AuditStore:
    def __init__(self, base_path: Path):
        self.base = base_path / "audit"
        self.base.mkdir(parents=True, exist_ok=True)

    def log(self, proposal_id: str, previous: ProposalState, new: ProposalState, actor: str, details: dict | None = None):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_state": previous.value,
            "new_state": new.value,
            "actor": actor,
            "details": details or {},
        }
        path = self.base / f"{proposal_id}.json"
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(record, fp, indent=2)

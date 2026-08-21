# src/domain/metrics.py
"""
Metrics collection for the mediation plane.

The design (docs/PHASE_2_IMPLEMENTATION_PLAN.md §2.4) calls for a *state‑queue inference* – we can compute run‑time counters such as how many proposals are currently in each state and total number processed.

This module defines :class:`MetricsCollector` which tracks:

* ``total_proposals`` – all proposals ever created.
* ``state_counts`` – current count per |ProposalState|.
* ``processing_times`` – latency from creation to terminal state for completed proposals.

All metrics are derived entirely from the mediation plane's public methods and do not require external libraries or persistence.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List

from .models import ProposalState

@dataclass
class _ProposalTimer:
    created_at: float
    finished_at: float | None = None

class MetricsCollector:
    """Collect metrics about proposal processing."""

    def __init__(self):
        self.total_proposals: int = 0
        # Current live count per state
        self.state_counts: Dict[str, int] = defaultdict(int)
        # Tracking creation times for latency calculation
        self._timers: Dict[str, _ProposalTimer] = {}

    def proposal_created(self, proposal_id: str):
        self.total_proposals += 1
        self.state_counts["PROPOSED"] += 1
        self._timers[proposal_id] = _ProposalTimer(time.time())

    def state_changed(self, proposal_id: str, new_state: ProposalState | str):
        current = None
        # Find any existing state for this id by scanning timers keys? We don't store old state
        # Instead we rely on caller to decrement prior state before calling. For simplicity,
        # callers must call decrement_old.
        self.state_counts[str(new_state)] += 1

    def decrement_state(self, proposal_id: str, old_state: ProposalState | str):
        key = str(old_state)
        if self.state_counts[key] > 0:
            self.state_counts[key] -= 1
        else:
            # Inconsistent state; ignore.
            pass

    def finished(self, proposal_id: str):
        timer = self._timers.get(proposal_id)
        if timer and not timer.finished_at:
            timer.finished_at = time.time()

    def get_metrics(self) -> dict:
        # Return immutable snapshot of metrics.
        result = {
            "total_proposals": self.total_proposals,
            "state_counts": dict(sorted(self.state_counts.items())),
            "process_times_ms": [
                int((t.finished_at - t.created_at) * 1000)
                for t in self._timers.values()
                if t.finished_at is not None
            ],
        }
        return result

# Singleton instance can be reused but we expose class to integrate with API.

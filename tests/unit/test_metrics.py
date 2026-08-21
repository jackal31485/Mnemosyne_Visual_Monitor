# tests/unit/test_metrics.py
import pytest
from src.domain.metrics import MetricsCollector, _ProposalTimer
from src.domain.api import MediationAPI

# Helper to create dummy request

def dummy_request(profile='p1', mem_id='m1'):
    return {"source_profile": profile, "source_memory_id": mem_id}

class TestMetricsCollector:
    def test_initial_metrics(self):
        mc = MetricsCollector()
        m = mc.get_metrics()
        assert m["total_proposals"] == 0
        assert m["state_counts"] == {}
        assert m["process_times_ms"] == []

    def test_proposal_count_and_state(self):
        mc = MetricsCollector()
        mc.proposal_created("id1")
        mc.proposal_created("id2")
        assert mc.total_proposals == 2
        counts = mc.state_counts
        assert counts["PROPOSED"] == 2

    def test_state_transition(self):
        mc = MetricsCollector()
        mc.proposal_created("pid1")
        # Transition to PRIVACY_FILTERING
        mc.decrement_state("pid1", "PROPOSED")
        mc.state_changed("pid1", "PRIVACY_FILTERING")
        assert mc.state_counts["PROPOSED"] == 0
        assert mc.state_counts["PRIVACY_FILTERING"] == 1

    def test_metrics_independent_collector(self):
        mc1 = MetricsCollector()
        mc2 = MetricsCollector()
        mc1.proposal_created("a")
        mc2.proposal_created("b")
        mc1.decrement_state("a", "PROPOSED")
        mc1.state_changed("a", "PRIVACY_FILTERING")
        # collectors should have separate state counts
        assert mc1.total_proposals == 1 and mc1.state_counts["PRIVACY_FILTERING"] == 1
        assert mc2.total_proposals == 1 and mc2.state_counts.get("PROPOSED", 0) == 1

class TestMediationAPIIntegration:
    def test_api_metrics_after_propose_and_validate(self):
        api = MediationAPI()
        # initial metrics should be zero
        assert api.get_metrics()["total_proposals"] == 0
        status, body = api.propose(dummy_request('profile1', 'memX'), 'profile1')
        assert status == 201
        # after propose, total proposals is 1 and state_counts PROPOSED=1
        m1 = api.get_metrics()
        assert m1["total_proposals"] == 1
        assert m1["state_counts"].get("PROPOSED") == 1
        pid = body['proposal_id']
        # validate proposal
        status, body2 = api.validate(pid)
        assert status in (200, 422)  # either accepted or rejected based on simple validator logic
        m_after = api.get_metrics()
        # In both cases PROPOSED should be decremented
        assert m_after["state_counts"].get("PROPOSED", 0) == 0
        # If validated, ready_for_promotion count increased
        if status == 200:
            assert m_after["state_counts"].get("READY_FOR_PROMOTION") == 1
        else:
            # rejected should have REJECTED state
            assert m_after["state_counts"].get("REJECTED", 0) == 1
        # process times recorded for finished proposals
        assert len(m_after["process_times_ms"]) >= (1 if status==200 else 0)


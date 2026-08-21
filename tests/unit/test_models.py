import sys, os
sys.path.append(os.path.join(os.getcwd(), "src"))
import pytest
from domain.models import Proposal, ProposalState

def test_default_proposal_state():
    p = Proposal(source_profile="athena", source_memory_id="mem123")
    assert p.state == ProposalState.PROPOSED

# Check that source_reference is set correctly

def test_source_reference_initialization():
    p = Proposal(source_profile="userA", source_memory_id="idX")
    assert p.source_reference.profile == "userA"
    assert p.source_reference.memory_id == "idX"

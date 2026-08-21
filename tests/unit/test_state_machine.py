import sys, os
sys.path.append(os.path.join(os.getcwd(), "src"))
import pytest
from domain.state_machine import next_state, ProposalState

# Helper to sequentially transition

def run_sequence(seq):
    state = ProposalState.PROPOSED
    for target in seq:
        state = next_state(state, target)
    return state


def test_valid_path_prog():
    final = run_sequence([
        ProposalState.PRIVACY_FILTERING,
        ProposalState.VALIDATING,
        ProposalState.READY_FOR_PROMOTION,
    ])
    assert final == ProposalState.READY_FOR_PROMOTION


def test_rejection_path():
    final = run_sequence([
        ProposalState.PRIVACY_FILTERING,
        ProposalState.VALIDATING,
        ProposalState.REJECTED,
    ])
    assert final == ProposalState.REJECTED


def test_manual_review_path():
    final = run_sequence([
        ProposalState.PRIVACY_FILTERING,
        ProposalState.VALIDATING,
        ProposalState.MANUAL_REVIEW,
        ProposalState.READY_FOR_PROMOTION,
    ])
    assert final == ProposalState.READY_FOR_PROMOTION


def test_invalid_transition():
    with pytest.raises(ValueError):
        next_state(ProposalState.PROPOSED, ProposalState.VALIDATING)


def test_terminal_no_transition():
    for terminal in (ProposalState.REJECTED, ProposalState.READY_FOR_PROMOTION):
        with pytest.raises(ValueError):
            next_state(terminal, ProposalState.PRIVACY_FILTERING)

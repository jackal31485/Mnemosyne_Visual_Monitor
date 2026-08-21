from enum import Enum
from domain.models import ProposalState, Proposal

def next_state(current: ProposalState, target: ProposalState) -> ProposalState:
    transitions = {
        ProposalState.PROPOSED: {ProposalState.PRIVACY_FILTERING},
        ProposalState.PRIVACY_FILTERING: {ProposalState.VALIDATING},
        ProposalState.VALIDATING: {
            ProposalState.REJECTED,
            ProposalState.READY_FOR_PROMOTION,
            ProposalState.MANUAL_REVIEW,
        },
        ProposalState.MANUAL_REVIEW: {ProposalState.READY_FOR_PROMOTION},
    }
    if current not in transitions:
        raise ValueError(f"No transitions defined for state {current}")
    if target not in transitions[current]:
        raise ValueError(f"Invalid transition from {current} to {target}")
    return target

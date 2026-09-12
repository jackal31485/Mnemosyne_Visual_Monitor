from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Sequence, Tuple

from src.domain.temporal_history_synthesis import (
    TemporalHistorySynthesis,
    synthesize_history,
)
from src.domain.temporal_state_history import TemporalStateHistory


class TemporalTrajectoryKind(str, Enum):
    EMPTY = "empty"
    STABLE = "stable"
    TRANSITION = "transition"
    REVERSAL = "reversal"
    OSCILLATION = "oscillation"
    DIVERGENT = "divergent"
    INCOMPLETE = "incomplete"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class TemporalTrajectory:
    """Deterministic descriptive classification of temporal histories."""

    subject_type: str
    subject_id: str
    kind: TemporalTrajectoryKind
    observation_count: int
    distinct_state_count: int
    transition_count: int
    reversal_count: int
    oscillation_count: int
    history_count: int
    has_divergence: bool
    has_incomplete_history: bool
    has_temporal_uncertainty: bool

    @property
    def is_stable(self) -> bool:
        return self.kind is TemporalTrajectoryKind.STABLE

    @property
    def is_transition(self) -> bool:
        return self.kind is TemporalTrajectoryKind.TRANSITION

    @property
    def is_reversal(self) -> bool:
        return self.kind is TemporalTrajectoryKind.REVERSAL

    @property
    def is_oscillating(self) -> bool:
        return self.kind is TemporalTrajectoryKind.OSCILLATION

    @property
    def is_divergent(self) -> bool:
        return self.kind is TemporalTrajectoryKind.DIVERGENT

    @property
    def is_incomplete(self) -> bool:
        return self.kind is TemporalTrajectoryKind.INCOMPLETE

    @property
    def is_uncertain(self) -> bool:
        return self.kind is TemporalTrajectoryKind.UNCERTAIN


def _state_sequence(history: TemporalStateHistory) -> Tuple[str, ...]:
    return tuple(str(state) for state in history.states)


def _transition_count(states: Sequence[str]) -> int:
    return sum(
        1
        for left, right in zip(states, states[1:])
        if left != right
    )


def _reversal_count(states: Sequence[str]) -> int:
    count = 0

    for index in range(2, len(states)):
        if states[index] == states[index - 2] and states[index] != states[index - 1]:
            count += 1

    return count


def _oscillation_count(states: Sequence[str]) -> int:
    """Count repeated A -> B -> A -> B cycles descriptively."""
    count = 0

    for index in range(3, len(states)):
        if (
            states[index] == states[index - 2]
            and states[index - 1] == states[index - 3]
            and states[index] != states[index - 1]
        ):
            count += 1

    return count


def _classify_single_history(
    history: TemporalStateHistory,
) -> tuple[
    TemporalTrajectoryKind,
    int,
    int,
    int,
]:
    states = _state_sequence(history)

    if not states:
        return TemporalTrajectoryKind.EMPTY, 0, 0, 0

    transition_count = _transition_count(states)
    reversal_count = _reversal_count(states)
    oscillation_count = _oscillation_count(states)

    if len(set(states)) == 1:
        return (
            TemporalTrajectoryKind.STABLE,
            transition_count,
            reversal_count,
            oscillation_count,
        )

    if oscillation_count > 0:
        kind = TemporalTrajectoryKind.OSCILLATION
    elif reversal_count > 0:
        kind = TemporalTrajectoryKind.REVERSAL
    elif transition_count == 1:
        kind = TemporalTrajectoryKind.TRANSITION
    else:
        kind = TemporalTrajectoryKind.TRANSITION

    return kind, transition_count, reversal_count, oscillation_count


def _classify_synthesis(
    synthesis: TemporalHistorySynthesis,
) -> TemporalTrajectoryKind:
    if synthesis.observation_count == 0:
        return TemporalTrajectoryKind.EMPTY

    if synthesis.has_divergence:
        return TemporalTrajectoryKind.DIVERGENT

    if synthesis.has_incomplete_history:
        return TemporalTrajectoryKind.INCOMPLETE

    if synthesis.has_temporal_uncertainty:
        return TemporalTrajectoryKind.UNCERTAIN

    states = tuple(str(state) for state in synthesis.consensus_states)

    if not states:
        return TemporalTrajectoryKind.EMPTY

    if len(set(states)) == 1:
        return TemporalTrajectoryKind.STABLE

    transitions = _transition_count(states)
    reversals = _reversal_count(states)
    oscillations = _oscillation_count(states)

    if oscillations:
        return TemporalTrajectoryKind.OSCILLATION

    if reversals:
        return TemporalTrajectoryKind.REVERSAL

    if transitions:
        return TemporalTrajectoryKind.TRANSITION

    return TemporalTrajectoryKind.STABLE


def classify_trajectory(
    histories: Iterable[TemporalStateHistory],
) -> TemporalTrajectory:
    """Classify one or more histories without selecting a truthful history."""
    histories = tuple(histories)

    if not histories:
        raise ValueError("histories must not be empty")

    synthesis = synthesize_history(histories)

    transition_count = 0
    reversal_count = 0
    oscillation_count = 0
    observation_count = 0
    distinct_states: List[str] = []

    for history in histories:
        states = _state_sequence(history)
        observation_count += len(states)

        for state in states:
            if state not in distinct_states:
                distinct_states.append(state)

        (
            _kind,
            transitions,
            reversals,
            oscillations,
        ) = _classify_single_history(history)

        transition_count += transitions
        reversal_count += reversals
        oscillation_count += oscillations

    return TemporalTrajectory(
        subject_type=synthesis.subject_type,
        subject_id=synthesis.subject_id,
        kind=_classify_synthesis(synthesis),
        observation_count=observation_count,
        distinct_state_count=len(distinct_states),
        transition_count=transition_count,
        reversal_count=reversal_count,
        oscillation_count=oscillation_count,
        history_count=len(histories),
        has_divergence=synthesis.has_divergence,
        has_incomplete_history=synthesis.has_incomplete_history,
        has_temporal_uncertainty=synthesis.has_temporal_uncertainty,
    )


def classify_trajectory_groups(
    histories_by_subject: dict[
        tuple[str, str],
        Iterable[TemporalStateHistory],
    ],
) -> dict[tuple[str, str], TemporalTrajectory]:
    """Classify subject histories in deterministic subject-key order."""
    result: dict[tuple[str, str], TemporalTrajectory] = {}

    for subject in sorted(histories_by_subject):
        result[subject] = classify_trajectory(
            histories_by_subject[subject]
        )

    return result

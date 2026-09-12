from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_history_consensus import TemporalHistoryConsensus
from .temporal_state_history import TemporalStateHistory


@dataclass(frozen=True, slots=True)
class TemporalHistorySynthesis:
    """Descriptive synthesis of one subject's temporal histories.

    This class summarizes observed histories and their consensus without
    selecting a canonical truth or modifying any source evidence.
    """

    subject_type: str
    subject_id: str
    history_count: int
    observation_count: int
    distinct_state_count: int
    initial_states: tuple[str, ...]
    final_states: tuple[str, ...]
    consensus_states: tuple[str, ...]
    divergent_positions: tuple[int, ...]
    incomplete_positions: tuple[int, ...]
    consensus_ratio: float
    disagreement_ratio: float
    coverage_ratio: float
    has_divergence: bool
    has_incomplete_history: bool
    has_temporal_uncertainty: bool

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")
        if self.history_count <= 0:
            raise ValueError("history_count must be positive")
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")
        if self.distinct_state_count < 0:
            raise ValueError("distinct_state_count must be non-negative")

        if not 0.0 <= self.consensus_ratio <= 1.0:
            raise ValueError("consensus_ratio must be between 0 and 1")
        if not 0.0 <= self.disagreement_ratio <= 1.0:
            raise ValueError("disagreement_ratio must be between 0 and 1")
        if not 0.0 <= self.coverage_ratio <= 1.0:
            raise ValueError("coverage_ratio must be between 0 and 1")

        if self.has_divergence != bool(self.divergent_positions):
            raise ValueError(
                "has_divergence must match divergent_positions"
            )

        if self.has_incomplete_history != bool(self.incomplete_positions):
            raise ValueError(
                "has_incomplete_history must match incomplete_positions"
            )

        if any(index < 0 for index in self.divergent_positions):
            raise ValueError("divergent positions must be non-negative")

        if any(index < 0 for index in self.incomplete_positions):
            raise ValueError("incomplete positions must be non-negative")

        if tuple(sorted(set(self.divergent_positions))) != self.divergent_positions:
            raise ValueError(
                "divergent_positions must be sorted and unique"
            )

        if tuple(sorted(set(self.incomplete_positions))) != self.incomplete_positions:
            raise ValueError(
                "incomplete_positions must be sorted and unique"
            )

    @property
    def has_consensus(self) -> bool:
        return bool(self.consensus_states)

    @property
    def is_stable(self) -> bool:
        return (
            not self.has_divergence
            and not self.has_incomplete_history
            and self.consensus_ratio == 1.0
        )

    @property
    def is_complete(self) -> bool:
        return not self.has_incomplete_history

    @property
    def is_uncertain(self) -> bool:
        return (
            self.has_temporal_uncertainty
            or self.has_divergence
            or self.has_incomplete_history
        )


def _assert_history(history: TemporalStateHistory) -> None:
    if not isinstance(history, TemporalStateHistory):
        raise TypeError("history must be a TemporalStateHistory")


def _assert_consensus(
    consensus: TemporalHistoryConsensus,
) -> None:
    if not isinstance(consensus, TemporalHistoryConsensus):
        raise TypeError(
            "consensus must be a TemporalHistoryConsensus"
        )


def _distinct_states(
    histories: tuple[TemporalStateHistory, ...],
) -> tuple[str, ...]:
    states: list[str] = []

    for history in histories:
        for state in history.states:
            if state not in states:
                states.append(state)

    return tuple(states)


def synthesize_history(
    histories: Iterable[TemporalStateHistory],
) -> TemporalHistorySynthesis:
    """Create a deterministic descriptive synthesis for one subject."""

    values = tuple(histories)

    if not values:
        raise ValueError("at least one history is required")

    for history in values:
        _assert_history(history)

    first = values[0]

    if any(
        history.subject_type != first.subject_type
        or history.subject_id != first.subject_id
        for history in values[1:]
    ):
        raise ValueError(
            "all histories must describe the same subject"
        )

    from .temporal_history_consensus import analyze_history_consensus

    consensus = analyze_history_consensus(values)

    return _synthesize(values, consensus)


def _synthesize(
    histories: tuple[TemporalStateHistory, ...],
    consensus: TemporalHistoryConsensus,
) -> TemporalHistorySynthesis:
    _assert_consensus(consensus)

    observation_count = sum(
        history.observation_count
        for history in histories
    )

    initial_states = tuple(
        history.initial_state
        for history in histories
        if history.initial_state is not None
    )

    final_states = tuple(
        history.final_state
        for history in histories
        if history.final_state is not None
    )

    consensus_states: list[str] = []
    divergent_positions: list[int] = []
    incomplete_positions: list[int] = []

    for position in consensus.positions:
        if len(position.states) == 1:
            if position.index not in [
                item.index
                for item in consensus.positions
                if item.index == position.index
            ]:
                continue

        if (
            position.index < len(position.states)
            and len(position.states) == 1
            and position.supporting_history_count == consensus.history_count
        ):
            consensus_states.append(position.states[0])

        if position.index < consensus.comparison_count:
            if position.index in [
                item.index
                for item in consensus.positions
                if item.index == position.index
            ]:
                if position.supporting_history_count < consensus.history_count:
                    if (
                        position.index
                        not in [
                            item.index
                            for item in consensus.positions
                            if item.index in incomplete_positions
                        ]
                    ):
                        if (
                            sum(
                                1
                                for history in histories
                                if position.index < history.observation_count
                            )
                            < consensus.history_count
                        ):
                            incomplete_positions.append(position.index)
                        else:
                            divergent_positions.append(position.index)

    # Reconstruct position classifications directly from histories. This
    # avoids treating a majority state as a consensus when histories disagree.
    divergent_positions = []
    incomplete_positions = []
    consensus_states = []

    for index in range(consensus.comparison_count):
        observed = tuple(
            history.states[index]
            for history in histories
            if index < history.observation_count
        )

        if len(observed) < len(histories):
            incomplete_positions.append(index)
            continue

        distinct = tuple(dict.fromkeys(observed))

        if len(distinct) == 1:
            consensus_states.append(distinct[0])
        else:
            divergent_positions.append(index)

    return TemporalHistorySynthesis(
        subject_type=histories[0].subject_type,
        subject_id=histories[0].subject_id,
        history_count=len(histories),
        observation_count=observation_count,
        distinct_state_count=len(_distinct_states(histories)),
        initial_states=initial_states,
        final_states=final_states,
        consensus_states=tuple(consensus_states),
        divergent_positions=tuple(divergent_positions),
        incomplete_positions=tuple(incomplete_positions),
        consensus_ratio=consensus.consensus_ratio,
        disagreement_ratio=consensus.disagreement_ratio,
        coverage_ratio=(
            observation_count
            / (len(histories) * consensus.comparison_count)
            if consensus.comparison_count
            else 0.0
        ),
        has_divergence=bool(divergent_positions),
        has_incomplete_history=bool(incomplete_positions),
        has_temporal_uncertainty=consensus.has_temporal_uncertainty,
    )


def synthesize_history_groups(
    histories: Iterable[TemporalStateHistory],
) -> tuple[TemporalHistorySynthesis, ...]:
    """Synthesize histories grouped deterministically by subject."""

    values = tuple(histories)

    if not values:
        return ()

    for history in values:
        _assert_history(history)

    groups: dict[tuple[str, str], list[TemporalStateHistory]] = {}

    for history in values:
        key = (
            history.subject_type,
            history.subject_id,
        )
        groups.setdefault(key, []).append(history)

    return tuple(
        synthesize_history(group)
        for _, group in sorted(groups.items())
    )

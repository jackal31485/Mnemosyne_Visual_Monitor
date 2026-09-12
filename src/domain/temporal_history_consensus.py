from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_state_history import TemporalStateHistory


@dataclass(frozen=True, slots=True)
class TemporalConsensusPosition:
    index: int
    states: tuple[str, ...]
    supporting_history_count: int
    total_history_count: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("index must be non-negative")

        if not self.states:
            raise ValueError("states must be non-empty")

        if self.supporting_history_count <= 0:
            raise ValueError("supporting_history_count must be positive")

        if self.total_history_count <= 0:
            raise ValueError("total_history_count must be positive")

        if self.supporting_history_count > self.total_history_count:
            raise ValueError(
                "supporting_history_count cannot exceed total_history_count"
            )


@dataclass(frozen=True, slots=True)
class TemporalHistoryConsensus:
    subject_type: str
    subject_id: str
    history_count: int
    comparison_count: int
    positions: tuple[TemporalConsensusPosition, ...]
    consensus_position_count: int
    disagreement_position_count: int
    incomplete_position_count: int
    has_disagreement: bool
    has_incomplete_history: bool
    has_temporal_uncertainty: bool

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")

        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        if self.history_count <= 0:
            raise ValueError("history_count must be positive")

        if self.comparison_count < 0:
            raise ValueError("comparison_count must be non-negative")

        if len(self.positions) != self.comparison_count:
            raise ValueError(
                "positions must match comparison_count"
            )

        if (
            self.consensus_position_count
            + self.disagreement_position_count
            + self.incomplete_position_count
            != self.comparison_count
        ):
            raise ValueError(
                "position classifications must sum to comparison_count"
            )

        if self.has_disagreement != (
            self.disagreement_position_count > 0
        ):
            raise ValueError(
                "has_disagreement must match disagreement count"
            )

        if self.has_incomplete_history != (
            self.incomplete_position_count > 0
        ):
            raise ValueError(
                "has_incomplete_history must match incomplete count"
            )

    @property
    def consensus_ratio(self) -> float:
        if self.comparison_count == 0:
            return 0.0

        return (
            self.consensus_position_count
            / self.comparison_count
        )

    @property
    def disagreement_ratio(self) -> float:
        if self.comparison_count == 0:
            return 0.0

        return (
            self.disagreement_position_count
            / self.comparison_count
        )


def _assert_history(history: TemporalStateHistory) -> None:
    if not isinstance(history, TemporalStateHistory):
        raise TypeError("history must be a TemporalStateHistory")


def _assert_same_subject(
    histories: tuple[TemporalStateHistory, ...],
) -> None:
    first = histories[0]

    for history in histories[1:]:
        if (
            history.subject_type != first.subject_type
            or history.subject_id != first.subject_id
        ):
            raise ValueError(
                "all histories must describe the same subject"
            )


def analyze_history_consensus(
    histories: Iterable[TemporalStateHistory],
) -> TemporalHistoryConsensus:
    values = tuple(histories)

    if not values:
        raise ValueError("at least one history is required")

    for history in values:
        _assert_history(history)

    _assert_same_subject(values)

    history_count = len(values)
    comparison_count = max(
        history.observation_count
        for history in values
    )

    positions: list[TemporalConsensusPosition] = []
    consensus_count = 0
    disagreement_count = 0
    incomplete_count = 0

    for index in range(comparison_count):
        states = tuple(
            history.states[index]
            for history in values
            if index < history.observation_count
        )

        distinct_states = tuple(dict.fromkeys(states))
        supporting_count = max(
            states.count(state)
            for state in distinct_states
        )

        complete = len(states) == history_count
        consensus = len(distinct_states) == 1
        disagreement = len(distinct_states) > 1

        if not complete:
            incomplete_count += 1
        elif consensus:
            consensus_count += 1
        elif disagreement:
            disagreement_count += 1

        positions.append(
            TemporalConsensusPosition(
                index=index,
                states=distinct_states,
                supporting_history_count=supporting_count,
                total_history_count=history_count,
            )
        )

    return TemporalHistoryConsensus(
        subject_type=values[0].subject_type,
        subject_id=values[0].subject_id,
        history_count=history_count,
        comparison_count=comparison_count,
        positions=tuple(positions),
        consensus_position_count=consensus_count,
        disagreement_position_count=disagreement_count,
        incomplete_position_count=incomplete_count,
        has_disagreement=disagreement_count > 0,
        has_incomplete_history=incomplete_count > 0,
        has_temporal_uncertainty=any(
            history.has_temporal_uncertainty
            for history in values
        ),
    )


def analyze_history_consensus_groups(
    histories: Iterable[TemporalStateHistory],
) -> tuple[TemporalHistoryConsensus, ...]:
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
        analyze_history_consensus(group)
        for _, group in sorted(groups.items())
    )

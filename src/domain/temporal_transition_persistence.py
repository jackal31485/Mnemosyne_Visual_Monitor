from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_change_points import TemporalStableRun


@dataclass(frozen=True, slots=True)
class TemporalStatePersistence:
    """Descriptive persistence of an observed state run."""

    state: str
    observation_count: int
    start_index: int
    end_index: int

    def __post_init__(self) -> None:
        if not self.state:
            raise ValueError("state must not be empty")
        if self.observation_count < 1:
            raise ValueError("observation_count must be positive")
        if self.start_index < 0 or self.end_index < self.start_index:
            raise ValueError("invalid run bounds")
        if self.observation_count != self.end_index - self.start_index + 1:
            raise ValueError("observation_count must match run bounds")

    @property
    def is_repeated(self) -> bool:
        return self.observation_count > 1


@dataclass(frozen=True, slots=True)
class TemporalTransitionPersistence:
    """Descriptive persistence summary for a sequence of stable runs."""

    subject_type: str
    subject_id: str
    runs: tuple[TemporalStatePersistence, ...]
    longest_persistence: int
    repeated_state_run_count: int

    def __post_init__(self) -> None:
        if not self.subject_type or not self.subject_id:
            raise ValueError("subject identity must be non-empty")
        if self.longest_persistence < 0:
            raise ValueError("longest_persistence must not be negative")
        if self.repeated_state_run_count < 0:
            raise ValueError("repeated_state_run_count must not be negative")

    @property
    def run_count(self) -> int:
        return len(self.runs)

    @property
    def has_persistence(self) -> bool:
        return self.longest_persistence > 1


def analyze_transition_persistence(
    subject_type: str,
    subject_id: str,
    runs: Iterable[TemporalStableRun],
) -> TemporalTransitionPersistence:
    if not subject_type or not subject_id:
        raise ValueError("subject identity must be non-empty")
    values = tuple(runs)
    for run in values:
        if not isinstance(run, TemporalStableRun):
            raise TypeError("runs must contain TemporalStableRun values")
    persistence = tuple(
        TemporalStatePersistence(
            state=run.state,
            observation_count=run.observation_count,
            start_index=run.start_index,
            end_index=run.end_index,
        )
        for run in values
    )
    return TemporalTransitionPersistence(
        subject_type=subject_type,
        subject_id=subject_id,
        runs=persistence,
        longest_persistence=max((r.observation_count for r in persistence), default=0),
        repeated_state_run_count=sum(r.is_repeated for r in persistence),
    )

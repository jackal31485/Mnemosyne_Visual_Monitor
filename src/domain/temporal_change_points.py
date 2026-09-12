from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_trajectory import TemporalTrajectory


@dataclass(frozen=True, slots=True)
class TemporalChangePoint:
    """A descriptive state change at an observation boundary."""

    index: int
    previous_state: str
    next_state: str

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("index must be positive")
        if not self.previous_state:
            raise ValueError("previous_state must not be empty")
        if not self.next_state:
            raise ValueError("next_state must not be empty")

    @property
    def transition(self) -> tuple[str, str]:
        return self.previous_state, self.next_state


@dataclass(frozen=True, slots=True)
class TemporalStableRun:
    """A contiguous run of the same observed state."""

    start_index: int
    end_index: int
    state: str

    def __post_init__(self) -> None:
        if self.start_index < 0:
            raise ValueError("start_index must not be negative")
        if self.end_index < self.start_index:
            raise ValueError("end_index must not precede start_index")
        if not self.state:
            raise ValueError("state must not be empty")

    @property
    def observation_count(self) -> int:
        return self.end_index - self.start_index + 1


@dataclass(frozen=True, slots=True)
class TemporalChangePointAnalysis:
    """Descriptive change-point analysis for one temporal trajectory."""

    subject_type: str
    subject_id: str
    observation_count: int
    change_point_count: int
    change_points: tuple[TemporalChangePoint, ...]
    stable_run_count: int
    stable_runs: tuple[TemporalStableRun, ...]
    longest_stable_run: int

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must not be empty")
        if not self.subject_id:
            raise ValueError("subject_id must not be empty")
        if self.observation_count < 0:
            raise ValueError("observation_count must not be negative")
        if self.change_point_count != len(self.change_points):
            raise ValueError(
                "change_point_count must match change_points"
            )
        if self.stable_run_count != len(self.stable_runs):
            raise ValueError("stable_run_count must match stable_runs")
        if self.longest_stable_run < 0:
            raise ValueError("longest_stable_run must not be negative")

    @property
    def has_change_points(self) -> bool:
        return self.change_point_count > 0

    @property
    def has_stable_runs(self) -> bool:
        return self.stable_run_count > 0


def _assert_trajectory(value: object) -> None:
    if not isinstance(value, TemporalTrajectory):
        raise TypeError("trajectory must be a TemporalTrajectory")


def _analyze_states(
    states: tuple[str, ...],
) -> tuple[
    tuple[TemporalChangePoint, ...],
    tuple[TemporalStableRun, ...],
]:
    if not states:
        return (), ()

    change_points: list[TemporalChangePoint] = []
    stable_runs: list[TemporalStableRun] = []

    run_start = 0
    current_state = states[0]

    for index in range(1, len(states)):
        next_state = states[index]

        if next_state != current_state:
            change_points.append(
                TemporalChangePoint(
                    index=index,
                    previous_state=current_state,
                    next_state=next_state,
                )
            )

            stable_runs.append(
                TemporalStableRun(
                    start_index=run_start,
                    end_index=index - 1,
                    state=current_state,
                )
            )

            run_start = index
            current_state = next_state

    stable_runs.append(
        TemporalStableRun(
            start_index=run_start,
            end_index=len(states) - 1,
            state=current_state,
        )
    )

    return tuple(change_points), tuple(stable_runs)


def analyze_change_points(
    trajectory: TemporalTrajectory,
    states: Iterable[str],
) -> TemporalChangePointAnalysis:
    """Analyze state changes in an explicitly supplied trajectory sequence."""

    _assert_trajectory(trajectory)

    states = tuple(str(state) for state in states)

    if len(states) != trajectory.observation_count:
        raise ValueError(
            "states length must match trajectory observation_count"
        )

    for state in states:
        if not state:
            raise ValueError("states must not contain empty values")

    change_points, stable_runs = _analyze_states(states)

    longest_stable_run = max(
        (run.observation_count for run in stable_runs),
        default=0,
    )

    return TemporalChangePointAnalysis(
        subject_type=trajectory.subject_type,
        subject_id=trajectory.subject_id,
        observation_count=len(states),
        change_point_count=len(change_points),
        change_points=change_points,
        stable_run_count=len(stable_runs),
        stable_runs=stable_runs,
        longest_stable_run=longest_stable_run,
    )


def analyze_change_point_groups(
    trajectories_by_subject: dict[
        tuple[str, str],
        tuple[TemporalTrajectory, Iterable[str]],
    ],
) -> dict[tuple[str, str], TemporalChangePointAnalysis]:
    """Analyze trajectories in deterministic subject-key order."""

    result: dict[
        tuple[str, str],
        TemporalChangePointAnalysis,
    ] = {}

    for subject in sorted(trajectories_by_subject):
        trajectory, states = trajectories_by_subject[subject]
        result[subject] = analyze_change_points(trajectory, states)

    return result

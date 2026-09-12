from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_state_timeline import TemporalStateTimeline
from .temporal_transition_analysis import TemporalTransitionAnalysis


@dataclass(frozen=True, slots=True)
class TemporalStateHistory:
    subject_type: str
    subject_id: str
    evidence_ids: tuple[int, ...]
    states: tuple[str, ...]
    initial_state: str | None
    final_state: str | None
    observation_count: int
    transition_count: int
    changed_transition_count: int
    unchanged_transition_count: int
    definite_transition_count: int
    indeterminate_transition_count: int

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")
        if self.observation_count != len(self.evidence_ids):
            raise ValueError("observation_count must match evidence_ids")
        if self.observation_count != len(self.states):
            raise ValueError("observation_count must match states")
        if self.transition_count != max(0, self.observation_count - 1):
            raise ValueError(
                "transition_count must equal observation_count minus one"
            )
        if (
            self.changed_transition_count
            + self.unchanged_transition_count
            != self.transition_count
        ):
            raise ValueError("transition counts must sum to transition_count")
        if (
            self.definite_transition_count
            + self.indeterminate_transition_count
            != self.transition_count
        ):
            raise ValueError(
                "certainty counts must sum to transition_count"
            )

        if self.observation_count == 0:
            if self.initial_state is not None or self.final_state is not None:
                raise ValueError(
                    "empty histories must not have initial or final states"
                )
        else:
            if self.initial_state != self.states[0]:
                raise ValueError("initial_state must match first state")
            if self.final_state != self.states[-1]:
                raise ValueError("final_state must match last state")

        if any(evidence_id <= 0 for evidence_id in self.evidence_ids):
            raise ValueError("evidence IDs must be positive")

        if any(not state for state in self.states):
            raise ValueError("states must be non-empty")

    @property
    def distinct_state_count(self) -> int:
        return len(set(self.states))

    @property
    def has_temporal_uncertainty(self) -> bool:
        return self.indeterminate_transition_count > 0

    @property
    def has_state_change(self) -> bool:
        return self.changed_transition_count > 0


def _assert_timeline(timeline: TemporalStateTimeline) -> None:
    if not isinstance(timeline, TemporalStateTimeline):
        raise TypeError("timeline must be a TemporalStateTimeline")


def summarize_state_history(
    timeline: TemporalStateTimeline,
) -> TemporalStateHistory:
    _assert_timeline(timeline)

    from .temporal_transition_analysis import analyze_state_timeline

    analysis = analyze_state_timeline(timeline)

    evidence_ids = tuple(entry.evidence_id for entry in timeline.entries)
    states = tuple(entry.state for entry in timeline.entries)

    return TemporalStateHistory(
        subject_type=timeline.subject_type,
        subject_id=timeline.subject_id,
        evidence_ids=evidence_ids,
        states=states,
        initial_state=states[0] if states else None,
        final_state=states[-1] if states else None,
        observation_count=len(states),
        transition_count=analysis.transition_count,
        changed_transition_count=analysis.changed_transition_count,
        unchanged_transition_count=analysis.unchanged_transition_count,
        definite_transition_count=analysis.definite_transition_count,
        indeterminate_transition_count=analysis.indeterminate_transition_count,
    )


def summarize_state_histories(
    timelines: Iterable[TemporalStateTimeline],
) -> tuple[TemporalStateHistory, ...]:
    values = tuple(timelines)

    for timeline in values:
        _assert_timeline(timeline)

    ordered = sorted(
        values,
        key=lambda timeline: (
            timeline.subject_type,
            timeline.subject_id,
        ),
    )

    return tuple(
        summarize_state_history(timeline)
        for timeline in ordered
    )

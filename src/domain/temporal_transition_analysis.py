from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_state_timeline import (
    TemporalStateTimeline,
    TemporalStateTransition,
)


@dataclass(frozen=True, slots=True)
class TemporalTransitionFinding:
    from_evidence_id: int
    to_evidence_id: int
    from_state: str
    to_state: str
    relation: str
    certainty: str
    state_changed: bool

    def __post_init__(self) -> None:
        if self.from_evidence_id <= 0 or self.to_evidence_id <= 0:
            raise ValueError("evidence IDs must be positive")
        if self.from_evidence_id == self.to_evidence_id:
            raise ValueError("transition evidence IDs must differ")
        if not self.from_state or not self.to_state:
            raise ValueError("states must be non-empty")
        if not self.relation:
            raise ValueError("relation must be non-empty")
        if self.certainty not in {"definite", "indeterminate"}:
            raise ValueError("certainty must be definite or indeterminate")


@dataclass(frozen=True, slots=True)
class TemporalTransitionAnalysis:
    subject_type: str
    subject_id: str
    findings: tuple[TemporalTransitionFinding, ...]

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

    @property
    def transition_count(self) -> int:
        return len(self.findings)

    @property
    def changed_transition_count(self) -> int:
        return sum(finding.state_changed for finding in self.findings)

    @property
    def unchanged_transition_count(self) -> int:
        return sum(not finding.state_changed for finding in self.findings)

    @property
    def definite_transition_count(self) -> int:
        return sum(
            finding.certainty == "definite"
            for finding in self.findings
        )

    @property
    def indeterminate_transition_count(self) -> int:
        return sum(
            finding.certainty == "indeterminate"
            for finding in self.findings
        )

    @property
    def changed_evidence_ids(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (finding.from_evidence_id, finding.to_evidence_id)
            for finding in self.findings
            if finding.state_changed
        )


def _assert_timeline(timeline: TemporalStateTimeline) -> None:
    if not isinstance(timeline, TemporalStateTimeline):
        raise TypeError("timeline must be a TemporalStateTimeline")


def _analyze_transition(
    transition: TemporalStateTransition,
) -> TemporalTransitionFinding:
    return TemporalTransitionFinding(
        from_evidence_id=transition.from_evidence_id,
        to_evidence_id=transition.to_evidence_id,
        from_state=transition.from_state,
        to_state=transition.to_state,
        relation=transition.relation,
        certainty=transition.certainty,
        state_changed=transition.from_state != transition.to_state,
    )


def analyze_state_timeline(
    timeline: TemporalStateTimeline,
) -> TemporalTransitionAnalysis:
    _assert_timeline(timeline)

    findings = tuple(
        _analyze_transition(transition)
        for transition in timeline.transitions
    )

    return TemporalTransitionAnalysis(
        subject_type=timeline.subject_type,
        subject_id=timeline.subject_id,
        findings=findings,
    )


def analyze_state_timelines(
    timelines: Iterable[TemporalStateTimeline],
) -> tuple[TemporalTransitionAnalysis, ...]:
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
        analyze_state_timeline(timeline)
        for timeline in ordered
    )

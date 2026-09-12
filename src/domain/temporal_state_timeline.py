from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_aggregation import TemporalEvidenceGroup
from .temporal_contradiction import TemporalStateAssertion
from .temporal_precision import compare_precision_intervals


@dataclass(frozen=True, slots=True)
class TemporalTimelineEntry:
    evidence_id: int
    subject_type: str
    subject_id: str
    state: str
    start: object
    end: object

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, int) or self.evidence_id <= 0:
            raise ValueError("evidence_id must be a positive integer")
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")
        if not self.state:
            raise ValueError("state must be non-empty")


@dataclass(frozen=True, slots=True)
class TemporalStateTransition:
    subject_type: str
    subject_id: str
    from_evidence_id: int
    to_evidence_id: int
    from_state: str
    to_state: str
    relation: str
    certainty: str

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")
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
class TemporalStateTimeline:
    subject_type: str
    subject_id: str
    entries: tuple[TemporalTimelineEntry, ...]
    transitions: tuple[TemporalStateTransition, ...]

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        for entry in self.entries:
            if (
                entry.subject_type != self.subject_type
                or entry.subject_id != self.subject_id
            ):
                raise ValueError("all entries must belong to the timeline subject")

        for transition in self.transitions:
            if (
                transition.subject_type != self.subject_type
                or transition.subject_id != self.subject_id
            ):
                raise ValueError("all transitions must belong to the timeline subject")


def _assert_group(group: TemporalEvidenceGroup) -> None:
    if not isinstance(group, TemporalEvidenceGroup):
        raise TypeError("group must be a TemporalEvidenceGroup")


def _entry(assertion: TemporalStateAssertion) -> TemporalTimelineEntry:
    return TemporalTimelineEntry(
        evidence_id=assertion.evidence_id,
        subject_type=assertion.subject_type,
        subject_id=assertion.subject_id,
        state=assertion.state,
        start=assertion.interval.start,
        end=assertion.interval.end,
    )


def build_state_timeline(
    group: TemporalEvidenceGroup,
) -> TemporalStateTimeline:
    _assert_group(group)

    ordered = tuple(
        sorted(
            group.assertions,
            key=lambda assertion: (
                assertion.interval.start,
                assertion.interval.end,
                assertion.evidence_id,
            ),
        )
    )

    entries = tuple(_entry(assertion) for assertion in ordered)
    transitions: list[TemporalStateTransition] = []

    for left, right in zip(ordered, ordered[1:]):
        comparison = compare_precision_intervals(
            left.interval,
            right.interval,
        )

        transitions.append(
            TemporalStateTransition(
                subject_type=group.subject_type,
                subject_id=group.subject_id,
                from_evidence_id=left.evidence_id,
                to_evidence_id=right.evidence_id,
                from_state=left.state,
                to_state=right.state,
                relation=comparison.relation,
                certainty=comparison.certainty,
            )
        )

    return TemporalStateTimeline(
        subject_type=group.subject_type,
        subject_id=group.subject_id,
        entries=entries,
        transitions=tuple(transitions),
    )


def build_state_timelines(
    groups: Iterable[TemporalEvidenceGroup],
) -> tuple[TemporalStateTimeline, ...]:
    values = tuple(groups)

    for group in values:
        _assert_group(group)

    ordered = sorted(
        values,
        key=lambda group: (group.subject_type, group.subject_id),
    )

    return tuple(build_state_timeline(group) for group in ordered)

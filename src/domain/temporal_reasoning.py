from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol


class TemporalEvidenceRecord(Protocol):
    temporal_evidence_id: int
    start_time: str | None
    end_time: str | None
    precision: str


@dataclass(frozen=True, slots=True)
class TemporalInterval:
    """A normalized temporal interval derived from governed evidence."""

    evidence_id: int
    start_time: datetime
    end_time: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, int):
            raise TypeError("evidence_id must be an integer")

        if not isinstance(self.start_time, datetime):
            raise TypeError("start_time must be a datetime")

        if not isinstance(self.end_time, datetime):
            raise TypeError("end_time must be a datetime")

        if self.start_time > self.end_time:
            raise ValueError("start_time must not be after end_time")


@dataclass(frozen=True, slots=True)
class TemporalRelationship:
    """A deterministic relationship between two temporal evidence records."""

    subject_evidence_id: int
    object_evidence_id: int
    relation: str

    def __post_init__(self) -> None:
        if not isinstance(self.subject_evidence_id, int):
            raise TypeError("subject_evidence_id must be an integer")

        if not isinstance(self.object_evidence_id, int):
            raise TypeError("object_evidence_id must be an integer")

        if self.subject_evidence_id == self.object_evidence_id:
            raise ValueError("temporal relationship requires two evidence records")

        if self.relation not in {
            "before",
            "after",
            "meets",
            "overlaps",
            "during",
            "contains",
            "starts",
            "started_by",
            "ends",
            "ended_by",
            "at",
        }:
            raise ValueError("unsupported temporal relationship")


def _parse_datetime(value: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError("temporal value must be a string")

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def evidence_to_interval(
    evidence: TemporalEvidenceRecord,
) -> TemporalInterval | None:
    """Convert bounded temporal evidence into a reasoning interval.

    Unbounded or unknown-precision evidence is deliberately excluded.
    The reasoning layer must never invent a missing endpoint.
    """

    if evidence.start_time is None:
        return None

    if evidence.precision == "unknown":
        return None

    start = _parse_datetime(evidence.start_time)

    if evidence.end_time is None:
        end = start
    else:
        end = _parse_datetime(evidence.end_time)

    return TemporalInterval(
        evidence_id=evidence.temporal_evidence_id,
        start_time=start,
        end_time=end,
    )


def _relation(
    left: TemporalInterval,
    right: TemporalInterval,
) -> str:
    if left.end_time < right.start_time:
        return "before"

    if left.end_time > right.end_time and left.start_time > right.start_time:
        return "after"

    if left.end_time == right.start_time:
        return "meets"

    if left.start_time == right.end_time:
        return "after"

    if (
        left.start_time == right.start_time
        and left.end_time == right.end_time
    ):
        return "at"

    if (
        left.start_time <= right.start_time
        and left.end_time >= right.end_time
    ):
        if left.start_time == right.start_time:
            return "started_by"
        if left.end_time == right.end_time:
            return "ended_by"
        return "contains"

    if (
        right.start_time <= left.start_time
        and right.end_time >= left.end_time
    ):
        if left.start_time == right.start_time:
            return "starts"
        if left.end_time == right.end_time:
            return "ends"
        return "during"

    if (
        left.start_time < right.end_time
        and left.end_time > right.start_time
    ):
        return "overlaps"

    if left.start_time > right.end_time:
        return "after"

    return "before"


def compare_intervals(
    left: TemporalInterval,
    right: TemporalInterval,
) -> TemporalRelationship:
    """Derive one deterministic relationship between two intervals."""

    if not isinstance(left, TemporalInterval):
        raise TypeError("left must be a TemporalInterval")

    if not isinstance(right, TemporalInterval):
        raise TypeError("right must be a TemporalInterval")

    return TemporalRelationship(
        subject_evidence_id=left.evidence_id,
        object_evidence_id=right.evidence_id,
        relation=_relation(left, right),
    )


def reason_over_evidence(
    evidence: Iterable[TemporalEvidenceRecord],
) -> tuple[TemporalRelationship, ...]:
    """Compare every pair of bounded temporal evidence records.

    Evidence ordering is preserved.  No persistence or inference beyond
    deterministic interval comparison occurs.
    """

    evidence_list = list(evidence)
    intervals: list[TemporalInterval] = []

    for item in evidence_list:
        interval = evidence_to_interval(item)
        if interval is not None:
            intervals.append(interval)

    relationships: list[TemporalRelationship] = []

    for index, left in enumerate(intervals):
        for right in intervals[index + 1 :]:
            relationships.append(compare_intervals(left, right))

    return tuple(relationships)

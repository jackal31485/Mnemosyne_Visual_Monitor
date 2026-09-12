from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


class TemporalEvidenceRecord(Protocol):
    temporal_evidence_id: int
    start_time: str | None
    end_time: str | None
    precision: str


SUPPORTED_PRECISIONS = {
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "second",
}


@dataclass(frozen=True, slots=True)
class PrecisionInterval:
    """Semantic temporal interval represented by explicit precision."""

    evidence_id: int
    start: datetime
    end: datetime
    precision: str

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, int):
            raise TypeError("evidence_id must be an integer")

        if not isinstance(self.start, datetime):
            raise TypeError("start must be a datetime")

        if not isinstance(self.end, datetime):
            raise TypeError("end must be a datetime")

        if self.precision not in SUPPORTED_PRECISIONS:
            raise ValueError("unsupported temporal precision")

        if self.start > self.end:
            raise ValueError("start must not be after end")


@dataclass(frozen=True, slots=True)
class PrecisionTemporalComparison:
    """Relationship plus certainty caused by temporal precision."""

    subject_evidence_id: int
    object_evidence_id: int
    relation: str
    certainty: str

    def __post_init__(self) -> None:
        if self.subject_evidence_id == self.object_evidence_id:
            raise ValueError("comparison requires two evidence records")

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
            "indeterminate",
        }:
            raise ValueError("unsupported temporal relation")

        if self.certainty not in {
            "definite",
            "indeterminate",
        }:
            raise ValueError("unsupported certainty")


def _parse_temporal_value(value: str, precision: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError("temporal value must be a string")

    value = value.strip()

    if precision == "year" and len(value) == 4:
        return datetime(int(value), 1, 1)

    if precision == "month" and len(value) == 7:
        return datetime.fromisoformat(f"{value}-01")

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _precision_end(start: datetime, precision: str) -> datetime:
    if precision == "year":
        return datetime(start.year, 12, 31, 23, 59, 59, 999999)

    if precision == "month":
        last_day = calendar.monthrange(start.year, start.month)[1]
        return datetime(
            start.year,
            start.month,
            last_day,
            23,
            59,
            59,
            999999,
        )

    if precision == "day":
        return start.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

    if precision == "hour":
        return start.replace(
            minute=59,
            second=59,
            microsecond=999999,
        )

    if precision == "minute":
        return start.replace(
            second=59,
            microsecond=999999,
        )

    if precision == "second":
        return start

    raise ValueError("unsupported temporal precision")


def _expand_value(
    value: str,
    precision: str,
) -> tuple[datetime, datetime]:
    start = _parse_temporal_value(value, precision)
    end = _precision_end(start, precision)
    return start, end


def evidence_to_precision_interval(
    evidence: TemporalEvidenceRecord,
) -> PrecisionInterval | None:
    """Convert explicit evidence into a semantic precision interval.

    The returned bounds describe the precision of the assertion. They do
    not claim that the underlying event occurred at the beginning of the
    precision unit.
    """

    precision = evidence.precision

    if precision == "unknown":
        return None

    if precision not in SUPPORTED_PRECISIONS:
        raise ValueError("unsupported temporal precision")

    if evidence.start_time is None:
        return None

    start, semantic_end = _expand_value(
        evidence.start_time,
        precision,
    )

    if evidence.end_time is None:
        end = semantic_end
    else:
        explicit_start, explicit_end = _expand_value(
            evidence.end_time,
            precision,
        )

        if explicit_start < start:
            raise ValueError(
                "temporal evidence end_time precedes start_time"
            )

        end = explicit_end

    return PrecisionInterval(
        evidence_id=evidence.temporal_evidence_id,
        start=start,
        end=end,
        precision=precision,
    )


def compare_precision_intervals(
    left: PrecisionInterval,
    right: PrecisionInterval,
) -> PrecisionTemporalComparison:
    """Compare semantic intervals without inventing event timestamps."""

    if not isinstance(left, PrecisionInterval):
        raise TypeError("left must be a PrecisionInterval")

    if not isinstance(right, PrecisionInterval):
        raise TypeError("right must be a PrecisionInterval")

    if left.end < right.start:
        relation = "before"
        certainty = "definite"
    elif left.start > right.end:
        relation = "after"
        certainty = "definite"
    elif left.end == right.start:
        relation = "meets"
        certainty = "definite"
    elif (
        left.start == right.start
        and left.end == right.end
    ):
        relation = "at"
        certainty = "definite"
    elif (
        left.start <= right.start
        and left.end >= right.end
    ):
        if left.start == right.start:
            relation = "started_by"
        elif left.end == right.end:
            relation = "ended_by"
        else:
            relation = "contains"
        certainty = "definite"
    elif (
        right.start <= left.start
        and right.end >= left.end
    ):
        if left.start == right.start:
            relation = "starts"
        elif left.end == right.end:
            relation = "ends"
        else:
            relation = "during"
        certainty = "definite"
    else:
        relation = "overlaps"
        certainty = "indeterminate"

    return PrecisionTemporalComparison(
        subject_evidence_id=left.evidence_id,
        object_evidence_id=right.evidence_id,
        relation=relation,
        certainty=certainty,
    )

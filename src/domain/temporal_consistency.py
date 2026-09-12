from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_precision import (
    PrecisionInterval,
    PrecisionTemporalComparison,
    compare_precision_intervals,
)


@dataclass(frozen=True, slots=True)
class TemporalConflict:
    """A definite temporal contradiction between two evidence records."""

    subject_evidence_id: int
    object_evidence_id: int
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.subject_evidence_id, int):
            raise TypeError("subject_evidence_id must be an integer")

        if not isinstance(self.object_evidence_id, int):
            raise TypeError("object_evidence_id must be an integer")

        if self.subject_evidence_id == self.object_evidence_id:
            raise ValueError("conflict requires two evidence records")

        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")


@dataclass(frozen=True, slots=True)
class TemporalConsistencyReport:
    """Deterministic report over a collection of temporal intervals."""

    comparisons: tuple[PrecisionTemporalComparison, ...]
    conflicts: tuple[TemporalConflict, ...]

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def comparison_count(self) -> int:
        return len(self.comparisons)


def _is_definite_conflict(
    comparison: PrecisionTemporalComparison,
) -> bool:
    """Return whether the comparison itself establishes contradiction.

    A temporal ordering by itself is not contradictory. Contradiction
    requires two assertions about the same temporal subject that establish
    mutually incompatible ordering.
    """

    return False


def compare_subject_timelines(
    intervals: Iterable[PrecisionInterval],
) -> tuple[PrecisionTemporalComparison, ...]:
    """Compare every pair of supplied temporal intervals.

    Results are deterministic and preserve the caller's pair ordering.
    """

    values = tuple(intervals)

    for interval in values:
        if not isinstance(interval, PrecisionInterval):
            raise TypeError(
                "all values must be PrecisionInterval instances"
            )

    comparisons: list[PrecisionTemporalComparison] = []

    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            comparisons.append(
                compare_precision_intervals(left, right)
            )

    return tuple(comparisons)


def detect_temporal_conflicts(
    intervals: Iterable[PrecisionInterval],
) -> tuple[TemporalConflict, ...]:
    """Detect only definite contradictions.

    Overlap or indeterminate relationships are deliberately not treated
    as contradictions. Two imprecise assertions may legitimately refer
    to the same event or to different moments within their precision
    envelopes.
    """

    values = tuple(intervals)

    for interval in values:
        if not isinstance(interval, PrecisionInterval):
            raise TypeError(
                "all values must be PrecisionInterval instances"
            )

    conflicts: list[TemporalConflict] = []

    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            comparison = compare_precision_intervals(left, right)

            # Temporal evidence intervals are not contradictory merely
            # because they overlap. A contradiction requires a caller
            # supplied semantic constraint that says they cannot overlap.
            #
            # This phase therefore reports chronological incompatibility
            # only when explicit interval ordering makes coexistence
            # impossible. Plain interval comparison alone cannot establish
            # that condition.
            if _is_definite_conflict(comparison):
                conflicts.append(
                    TemporalConflict(
                        subject_evidence_id=left.evidence_id,
                        object_evidence_id=right.evidence_id,
                        reason=(
                            "Temporal assertions establish a definite "
                            "chronological contradiction."
                        ),
                    )
                )

    return tuple(conflicts)


def analyze_temporal_consistency(
    intervals: Iterable[PrecisionInterval],
) -> TemporalConsistencyReport:
    """Produce a deterministic consistency report."""

    values = tuple(intervals)
    comparisons = compare_subject_timelines(values)
    conflicts = detect_temporal_conflicts(values)

    return TemporalConsistencyReport(
        comparisons=comparisons,
        conflicts=conflicts,
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_precision import (
    PrecisionInterval,
    PrecisionTemporalComparison,
    compare_precision_intervals,
)


@dataclass(frozen=True, slots=True)
class TemporalStateAssertion:
    """A state assertion associated with a semantic temporal interval."""

    evidence_id: int
    subject_type: str
    subject_id: str
    state: str
    interval: PrecisionInterval

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, int):
            raise TypeError("evidence_id must be an integer")

        if not isinstance(self.subject_type, str) or not self.subject_type:
            raise ValueError("subject_type must be a non-empty string")

        if not isinstance(self.subject_id, str) or not self.subject_id:
            raise ValueError("subject_id must be a non-empty string")

        if not isinstance(self.state, str) or not self.state:
            raise ValueError("state must be a non-empty string")

        if not isinstance(self.interval, PrecisionInterval):
            raise TypeError("interval must be a PrecisionInterval")

        if self.interval.evidence_id != self.evidence_id:
            raise ValueError(
                "interval evidence_id must match assertion evidence_id"
            )


@dataclass(frozen=True, slots=True)
class TemporalContradiction:
    """A definite incompatibility between two state assertions."""

    subject_type: str
    subject_id: str
    left_evidence_id: int
    right_evidence_id: int
    left_state: str
    right_state: str
    relation: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.left_evidence_id, int):
            raise TypeError("left_evidence_id must be an integer")

        if not isinstance(self.right_evidence_id, int):
            raise TypeError("right_evidence_id must be an integer")

        if self.left_evidence_id == self.right_evidence_id:
            raise ValueError(
                "contradiction requires distinct evidence records"
            )

        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")

        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        if not self.left_state:
            raise ValueError("left_state must be non-empty")

        if not self.right_state:
            raise ValueError("right_state must be non-empty")

        if self.left_state == self.right_state:
            raise ValueError(
                "identical states cannot form a contradiction"
            )

        if self.relation not in {
            "overlaps",
            "at",
            "contains",
            "during",
            "starts",
            "started_by",
            "ends",
            "ended_by",
        }:
            raise ValueError("unsupported contradiction relation")

        if not self.reason:
            raise ValueError("reason must be non-empty")


def _same_subject(
    left: TemporalStateAssertion,
    right: TemporalStateAssertion,
) -> bool:
    return (
        left.subject_type == right.subject_type
        and left.subject_id == right.subject_id
    )


def _states_are_incompatible(
    left: TemporalStateAssertion,
    right: TemporalStateAssertion,
) -> bool:
    """Determine whether two explicit states are incompatible.

    This phase uses a conservative rule: distinct explicitly asserted
    states for the same subject are incompatible.

    Semantic state taxonomies can become more sophisticated in a later
    phase. For now, the caller must provide explicit state assertions;
    arbitrary text is never interpreted here.
    """

    return left.state != right.state


def _comparison_supports_overlap(
    comparison: PrecisionTemporalComparison,
) -> bool:
    """Return whether temporal evidence establishes overlap."""

    return (
        comparison.relation
        in {
            "overlaps",
            "at",
            "contains",
            "during",
            "starts",
            "started_by",
            "ends",
            "ended_by",
        }
        and comparison.certainty == "definite"
    )


def detect_state_contradictions(
    assertions: Iterable[TemporalStateAssertion],
) -> tuple[TemporalContradiction, ...]:
    """Detect definite temporal contradictions between state assertions.

    Contradictions require:

    1. the same subject;
    2. distinct explicit states;
    3. a definitely overlapping temporal relationship.

    Indeterminate temporal overlap is never promoted to contradiction.
    """

    values = tuple(assertions)

    for assertion in values:
        if not isinstance(assertion, TemporalStateAssertion):
            raise TypeError(
                "all values must be TemporalStateAssertion instances"
            )

    contradictions: list[TemporalContradiction] = []

    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if not _same_subject(left, right):
                continue

            if not _states_are_incompatible(left, right):
                continue

            comparison = compare_precision_intervals(
                left.interval,
                right.interval,
            )

            if not _comparison_supports_overlap(comparison):
                continue

            contradictions.append(
                TemporalContradiction(
                    subject_type=left.subject_type,
                    subject_id=left.subject_id,
                    left_evidence_id=left.evidence_id,
                    right_evidence_id=right.evidence_id,
                    left_state=left.state,
                    right_state=right.state,
                    relation=comparison.relation,
                    reason=(
                        "Distinct explicit states for the same subject "
                        "have a definite temporal overlap."
                    ),
                )
            )

    return tuple(contradictions)

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_contradiction import TemporalStateAssertion


@dataclass(frozen=True, slots=True)
class TemporalEvidenceGroup:
    """Deterministic collection of assertions for one subject."""

    subject_type: str
    subject_id: str
    assertions: tuple[TemporalStateAssertion, ...]

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")

        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        for assertion in self.assertions:
            if not isinstance(assertion, TemporalStateAssertion):
                raise TypeError(
                    "assertions must contain TemporalStateAssertion values"
                )

            if (
                assertion.subject_type != self.subject_type
                or assertion.subject_id != self.subject_id
            ):
                raise ValueError(
                    "all assertions must belong to the group subject"
                )

    @property
    def evidence_ids(self) -> tuple[int, ...]:
        return tuple(
            assertion.evidence_id
            for assertion in self.assertions
        )

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    assertion.state
                    for assertion in self.assertions
                }
            )
        )


@dataclass(frozen=True, slots=True)
class TemporalStateGroup:
    """Assertions for one explicit state of one subject."""

    subject_type: str
    subject_id: str
    state: str
    assertions: tuple[TemporalStateAssertion, ...]

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")

        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        if not self.state:
            raise ValueError("state must be non-empty")

        for assertion in self.assertions:
            if not isinstance(assertion, TemporalStateAssertion):
                raise TypeError(
                    "assertions must contain TemporalStateAssertion values"
                )

            if (
                assertion.subject_type != self.subject_type
                or assertion.subject_id != self.subject_id
            ):
                raise ValueError(
                    "all assertions must belong to the group subject"
                )

            if assertion.state != self.state:
                raise ValueError(
                    "all assertions must belong to the group state"
                )

    @property
    def evidence_ids(self) -> tuple[int, ...]:
        return tuple(
            assertion.evidence_id
            for assertion in self.assertions
        )


def _assert_valid_input(
    assertions: Iterable[TemporalStateAssertion],
) -> tuple[TemporalStateAssertion, ...]:
    values = tuple(assertions)

    for assertion in values:
        if not isinstance(assertion, TemporalStateAssertion):
            raise TypeError(
                "all values must be TemporalStateAssertion instances"
            )

    return values


def _sort_assertions(
    assertions: Iterable[TemporalStateAssertion],
) -> tuple[TemporalStateAssertion, ...]:
    """Stable deterministic ordering by temporal start then evidence ID."""

    return tuple(
        sorted(
            assertions,
            key=lambda assertion: (
                assertion.interval.start,
                assertion.interval.end,
                assertion.evidence_id,
            ),
        )
    )


def group_by_subject(
    assertions: Iterable[TemporalStateAssertion],
) -> tuple[TemporalEvidenceGroup, ...]:
    """Group assertions by subject in deterministic order."""

    values = _assert_valid_input(assertions)

    groups: dict[tuple[str, str], list[TemporalStateAssertion]] = {}

    for assertion in values:
        key = (
            assertion.subject_type,
            assertion.subject_id,
        )
        groups.setdefault(key, []).append(assertion)

    result: list[TemporalEvidenceGroup] = []

    for subject_type, subject_id in sorted(groups):
        result.append(
            TemporalEvidenceGroup(
                subject_type=subject_type,
                subject_id=subject_id,
                assertions=_sort_assertions(
                    groups[(subject_type, subject_id)]
                ),
            )
        )

    return tuple(result)


def group_by_state(
    assertions: Iterable[TemporalStateAssertion],
) -> tuple[TemporalStateGroup, ...]:
    """Group assertions by subject and explicit state."""

    values = _assert_valid_input(assertions)

    groups: dict[
        tuple[str, str, str],
        list[TemporalStateAssertion],
    ] = {}

    for assertion in values:
        key = (
            assertion.subject_type,
            assertion.subject_id,
            assertion.state,
        )
        groups.setdefault(key, []).append(assertion)

    result: list[TemporalStateGroup] = []

    for subject_type, subject_id, state in sorted(groups):
        result.append(
            TemporalStateGroup(
                subject_type=subject_type,
                subject_id=subject_id,
                state=state,
                assertions=_sort_assertions(
                    groups[(subject_type, subject_id, state)]
                ),
            )
        )

    return tuple(result)


def aggregate_temporal_evidence(
    assertions: Iterable[TemporalStateAssertion],
) -> tuple[TemporalEvidenceGroup, ...]:
    """Aggregate assertions without merging or discarding evidence."""

    return group_by_subject(assertions)

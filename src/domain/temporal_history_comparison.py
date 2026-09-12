from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_state_history import TemporalStateHistory


@dataclass(frozen=True, slots=True)
class TemporalHistoryComparison:
    subject_type: str
    subject_id: str
    left_evidence_ids: tuple[int, ...]
    right_evidence_ids: tuple[int, ...]
    matching_states: tuple[tuple[int, int, str], ...]
    divergent_states: tuple[
        tuple[int | None, int | None, str | None, str | None], ...
    ]
    left_only_states: tuple[tuple[int, str], ...]
    right_only_states: tuple[tuple[int, str], ...]
    temporal_uncertainty: bool
    comparison_count: int

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        if any(evidence_id <= 0 for evidence_id in self.left_evidence_ids):
            raise ValueError("left evidence IDs must be positive")
        if any(evidence_id <= 0 for evidence_id in self.right_evidence_ids):
            raise ValueError("right evidence IDs must be positive")

        expected_count = max(
            len(self.left_evidence_ids),
            len(self.right_evidence_ids),
        )
        if self.comparison_count != expected_count:
            raise ValueError(
                "comparison_count must equal the longer history length"
            )

        for left_id, right_id, state in self.matching_states:
            if left_id <= 0 or right_id <= 0:
                raise ValueError("matching evidence IDs must be positive")
            if not state:
                raise ValueError("matching states must be non-empty")

        for left_id, right_id, left_state, right_state in self.divergent_states:
            if left_id is not None and left_id <= 0:
                raise ValueError(
                    "divergent left evidence IDs must be positive"
                )
            if right_id is not None and right_id <= 0:
                raise ValueError(
                    "divergent right evidence IDs must be positive"
                )

            if left_state is None and right_state is None:
                raise ValueError(
                    "divergent states must contain at least one state"
                )

            if (
                left_state is not None
                and right_state is not None
                and left_state == right_state
            ):
                raise ValueError(
                    "matching states must not appear as divergent states"
                )

        for evidence_id, state in self.left_only_states:
            if evidence_id <= 0:
                raise ValueError("left-only evidence IDs must be positive")
            if not state:
                raise ValueError("left-only states must be non-empty")

        for evidence_id, state in self.right_only_states:
            if evidence_id <= 0:
                raise ValueError("right-only evidence IDs must be positive")
            if not state:
                raise ValueError("right-only states must be non-empty")

    @property
    def shared_state_count(self) -> int:
        return len(self.matching_states)

    @property
    def divergent_state_count(self) -> int:
        return len(self.divergent_states)

    @property
    def has_divergence(self) -> bool:
        return bool(self.divergent_states)

    @property
    def has_temporal_uncertainty(self) -> bool:
        return self.temporal_uncertainty


def _assert_history(history: TemporalStateHistory) -> None:
    if not isinstance(history, TemporalStateHistory):
        raise TypeError("history must be a TemporalStateHistory")


def _assert_same_subject(
    left: TemporalStateHistory,
    right: TemporalStateHistory,
) -> None:
    if (
        left.subject_type != right.subject_type
        or left.subject_id != right.subject_id
    ):
        raise ValueError("histories must describe the same subject")


def compare_state_histories(
    left: TemporalStateHistory,
    right: TemporalStateHistory,
) -> TemporalHistoryComparison:
    _assert_history(left)
    _assert_history(right)
    _assert_same_subject(left, right)

    comparison_count = max(
        left.observation_count,
        right.observation_count,
    )

    matching_states: list[tuple[int, int, str]] = []
    divergent_states: list[
        tuple[int | None, int | None, str | None, str | None]
    ] = []
    left_only_states: list[tuple[int, str]] = []
    right_only_states: list[tuple[int, str]] = []

    shared_count = min(
        left.observation_count,
        right.observation_count,
    )

    for index in range(shared_count):
        left_evidence_id = left.evidence_ids[index]
        right_evidence_id = right.evidence_ids[index]
        left_state = left.states[index]
        right_state = right.states[index]

        if left_state == right_state:
            matching_states.append(
                (
                    left_evidence_id,
                    right_evidence_id,
                    left_state,
                )
            )
        else:
            divergent_states.append(
                (
                    left_evidence_id,
                    right_evidence_id,
                    left_state,
                    right_state,
                )
            )

    if left.observation_count > shared_count:
        for index in range(shared_count, left.observation_count):
            left_only_states.append(
                (
                    left.evidence_ids[index],
                    left.states[index],
                )
            )
            divergent_states.append(
                (
                    left.evidence_ids[index],
                    None,
                    left.states[index],
                    None,
                )
            )

    if right.observation_count > shared_count:
        for index in range(shared_count, right.observation_count):
            right_only_states.append(
                (
                    right.evidence_ids[index],
                    right.states[index],
                )
            )
            divergent_states.append(
                (
                    None,
                    right.evidence_ids[index],
                    None,
                    right.states[index],
                )
            )

    return TemporalHistoryComparison(
        subject_type=left.subject_type,
        subject_id=left.subject_id,
        left_evidence_ids=left.evidence_ids,
        right_evidence_ids=right.evidence_ids,
        matching_states=tuple(matching_states),
        divergent_states=tuple(divergent_states),
        left_only_states=tuple(left_only_states),
        right_only_states=tuple(right_only_states),
        temporal_uncertainty=(
            left.has_temporal_uncertainty
            or right.has_temporal_uncertainty
        ),
        comparison_count=comparison_count,
    )


def compare_state_history_pairs(
    pairs: Iterable[
        tuple[TemporalStateHistory, TemporalStateHistory]
    ],
) -> tuple[TemporalHistoryComparison, ...]:
    values = tuple(pairs)

    for left, right in values:
        _assert_history(left)
        _assert_history(right)
        _assert_same_subject(left, right)

    ordered = sorted(
        values,
        key=lambda pair: (
            pair[0].subject_type,
            pair[0].subject_id,
        ),
    )

    return tuple(
        compare_state_histories(left, right)
        for left, right in ordered
    )

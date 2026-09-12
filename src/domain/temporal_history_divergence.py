from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_history_comparison import (
    TemporalHistoryComparison,
    compare_state_histories,
)
from .temporal_state_history import TemporalStateHistory


@dataclass(frozen=True, slots=True)
class TemporalHistoryDivergence:
    subject_type: str
    subject_id: str
    comparison_count: int
    shared_state_count: int
    divergent_state_count: int
    left_only_count: int
    right_only_count: int
    first_divergence_index: int | None
    agreement_ratio: float
    divergence_ratio: float
    has_divergence: bool
    has_asymmetric_observations: bool
    has_temporal_uncertainty: bool

    def __post_init__(self) -> None:
        if not self.subject_type:
            raise ValueError("subject_type must be non-empty")
        if not self.subject_id:
            raise ValueError("subject_id must be non-empty")

        if self.comparison_count < 0:
            raise ValueError("comparison_count must be non-negative")

        if self.shared_state_count < 0:
            raise ValueError("shared_state_count must be non-negative")

        if self.divergent_state_count < 0:
            raise ValueError("divergent_state_count must be non-negative")

        if self.left_only_count < 0:
            raise ValueError("left_only_count must be non-negative")

        if self.right_only_count < 0:
            raise ValueError("right_only_count must be non-negative")

        if not 0.0 <= self.agreement_ratio <= 1.0:
            raise ValueError("agreement_ratio must be between 0 and 1")

        if not 0.0 <= self.divergence_ratio <= 1.0:
            raise ValueError("divergence_ratio must be between 0 and 1")

        if self.comparison_count == 0:
            if self.agreement_ratio != 0.0:
                raise ValueError(
                    "empty comparisons must have zero agreement ratio"
                )
            if self.divergence_ratio != 0.0:
                raise ValueError(
                    "empty comparisons must have zero divergence ratio"
                )

        if self.first_divergence_index is not None:
            if self.first_divergence_index < 0:
                raise ValueError(
                    "first_divergence_index must be non-negative"
                )
            if self.first_divergence_index >= self.comparison_count:
                raise ValueError(
                    "first_divergence_index must be within comparison count"
                )

        if self.has_divergence != (self.divergent_state_count > 0):
            raise ValueError(
                "has_divergence must match divergent_state_count"
            )

        if self.has_asymmetric_observations != (
            self.left_only_count > 0 or self.right_only_count > 0
        ):
            raise ValueError(
                "has_asymmetric_observations must match asymmetric counts"
            )

    @property
    def is_fully_agreeing(self) -> bool:
        return not self.has_divergence and not self.has_asymmetric_observations

    @property
    def is_empty(self) -> bool:
        return self.comparison_count == 0


def _assert_comparison(
    comparison: TemporalHistoryComparison,
) -> None:
    if not isinstance(comparison, TemporalHistoryComparison):
        raise TypeError(
            "comparison must be a TemporalHistoryComparison"
        )


def analyze_history_divergence(
    comparison: TemporalHistoryComparison,
) -> TemporalHistoryDivergence:
    _assert_comparison(comparison)

    first_divergence_index: int | None = None

    if comparison.divergent_states:
        for index in range(comparison.comparison_count):
            if index >= len(comparison.left_evidence_ids):
                first_divergence_index = index
                break

            if index >= len(comparison.right_evidence_ids):
                first_divergence_index = index
                break

            left_state = comparison.left_evidence_ids[index]
            right_state = comparison.right_evidence_ids[index]

            matching = any(
                match[0] == left_state and match[1] == right_state
                for match in comparison.matching_states
            )

            if not matching:
                first_divergence_index = index
                break

    shared_count = comparison.shared_state_count
    divergent_count = comparison.divergent_state_count
    comparison_count = comparison.comparison_count

    if comparison_count:
        agreement_ratio = shared_count / comparison_count
        divergence_ratio = divergent_count / comparison_count
    else:
        agreement_ratio = 0.0
        divergence_ratio = 0.0

    return TemporalHistoryDivergence(
        subject_type=comparison.subject_type,
        subject_id=comparison.subject_id,
        comparison_count=comparison_count,
        shared_state_count=shared_count,
        divergent_state_count=divergent_count,
        left_only_count=len(comparison.left_only_states),
        right_only_count=len(comparison.right_only_states),
        first_divergence_index=first_divergence_index,
        agreement_ratio=agreement_ratio,
        divergence_ratio=divergence_ratio,
        has_divergence=comparison.has_divergence,
        has_asymmetric_observations=(
            bool(comparison.left_only_states)
            or bool(comparison.right_only_states)
        ),
        has_temporal_uncertainty=comparison.temporal_uncertainty,
    )


def compare_and_analyze_history_divergence(
    left: TemporalStateHistory,
    right: TemporalStateHistory,
) -> TemporalHistoryDivergence:
    return analyze_history_divergence(
        compare_state_histories(left, right)
    )


def analyze_history_divergences(
    comparisons: Iterable[TemporalHistoryComparison],
) -> tuple[TemporalHistoryDivergence, ...]:
    values = tuple(comparisons)

    for comparison in values:
        _assert_comparison(comparison)

    ordered = sorted(
        values,
        key=lambda comparison: (
            comparison.subject_type,
            comparison.subject_id,
        ),
    )

    return tuple(
        analyze_history_divergence(comparison)
        for comparison in ordered
    )

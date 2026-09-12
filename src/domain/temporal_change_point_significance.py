from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .temporal_change_points import TemporalChangePointAnalysis


@dataclass(frozen=True, slots=True)
class TemporalChangePointSignificance:
    """Descriptive significance of one observed state change."""

    index: int
    previous_state: str
    next_state: str
    observations_before: int
    observations_after: int
    persistence_before: int
    persistence_after: int

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("index must be positive")
        if not self.previous_state or not self.next_state:
            raise ValueError("states must be non-empty")
        for value in (
            self.observations_before,
            self.observations_after,
            self.persistence_before,
            self.persistence_after,
        ):
            if value < 0:
                raise ValueError("observation values must not be negative")

    @property
    def persistence_score(self) -> int:
        return min(self.persistence_before, self.persistence_after)

    @property
    def is_persistent(self) -> bool:
        return self.persistence_score > 1


@dataclass(frozen=True, slots=True)
class TemporalChangePointSignificanceAnalysis:
    """Descriptive significance analysis for observed change points."""

    subject_type: str
    subject_id: str
    change_points: tuple[TemporalChangePointSignificance, ...]
    persistent_change_point_count: int

    def __post_init__(self) -> None:
        if not self.subject_type or not self.subject_id:
            raise ValueError("subject identity must be non-empty")
        if self.persistent_change_point_count < 0:
            raise ValueError("persistent_change_point_count must not be negative")
        if self.persistent_change_point_count > len(self.change_points):
            raise ValueError("persistent count must not exceed change points")

    @property
    def change_point_count(self) -> int:
        return len(self.change_points)


def analyze_change_point_significance(
    analysis: TemporalChangePointAnalysis,
) -> TemporalChangePointSignificanceAnalysis:
    if not isinstance(analysis, TemporalChangePointAnalysis):
        raise TypeError("analysis must be a TemporalChangePointAnalysis")

    results: list[TemporalChangePointSignificance] = []
    runs = analysis.stable_runs
    for point in analysis.change_points:
        before = runs[next(i for i, run in enumerate(runs) if run.end_index == point.index - 1)]
        after = runs[next(i for i, run in enumerate(runs) if run.start_index == point.index)]
        results.append(
            TemporalChangePointSignificance(
                index=point.index,
                previous_state=point.previous_state,
                next_state=point.next_state,
                observations_before=before.observation_count,
                observations_after=after.observation_count,
                persistence_before=before.observation_count,
                persistence_after=after.observation_count,
            )
        )

    return TemporalChangePointSignificanceAnalysis(
        subject_type=analysis.subject_type,
        subject_id=analysis.subject_id,
        change_points=tuple(results),
        persistent_change_point_count=sum(r.is_persistent for r in results),
    )


def analyze_change_point_significance_groups(
    analyses_by_subject: dict[tuple[str, str], TemporalChangePointAnalysis],
) -> dict[tuple[str, str], TemporalChangePointSignificanceAnalysis]:
    return {
        subject: analyze_change_point_significance(analyses_by_subject[subject])
        for subject in sorted(analyses_by_subject)
    }

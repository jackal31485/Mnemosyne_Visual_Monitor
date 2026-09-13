from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.domain.temporal_contradiction import (
    TemporalContradiction,
    TemporalStateAssertion,
    detect_state_contradictions,
)


@dataclass(frozen=True, slots=True)
class TemporalConflictResult:
    """Immutable result of governed temporal contradiction detection."""

    contradictions: tuple[TemporalContradiction, ...]

    @property
    def conflict_count(self) -> int:
        return len(self.contradictions)


class TemporalConflictService:
    """Service facade for canonical temporal contradiction detection.

    This service delegates contradiction semantics to the canonical
    ``detect_state_contradictions`` domain function.

    It does not:
      - invent state assertions;
      - infer missing dates;
      - reinterpret temporal precision;
      - resolve entities;
      - persist conflicts;
      - promote contradictions;
      - modify source memories;
      - replace temporal retrieval or ranking.
    """

    def detect(
        self,
        assertions: Iterable[TemporalStateAssertion],
    ) -> TemporalConflictResult:
        """Detect definite contradictions in explicit state assertions."""
        contradictions = detect_state_contradictions(assertions)

        return TemporalConflictResult(
            contradictions=contradictions,
        )

    def detect_many(
        self,
        assertion_groups: Iterable[Iterable[TemporalStateAssertion]],
    ) -> tuple[TemporalConflictResult, ...]:
        """Detect contradictions independently for multiple assertion groups."""
        return tuple(
            self.detect(assertion_group)
            for assertion_group in assertion_groups
        )

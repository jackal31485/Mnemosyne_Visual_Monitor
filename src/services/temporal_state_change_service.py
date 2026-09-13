from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.domain.temporal_change import TemporalChangeAssertion


@dataclass(frozen=True, slots=True)
class TemporalStateChange:
    """Evidence-backed representation of a detected state change.

    This is a derived interpretation of an existing TemporalChangeAssertion.
    It is not a replacement for governed temporal evidence and is not
    independently persisted.

    No dates, values, entities, or relationships are inferred here.
    """

    assertion: TemporalChangeAssertion

    @property
    def subject(self):
        return self.assertion.subject

    @property
    def previous_value(self):
        return self.assertion.previous_value

    @property
    def new_value(self):
        return self.assertion.new_value


@dataclass(frozen=True, slots=True)
class TemporalStateChangeResult:
    """Immutable collection of evidence-backed state changes."""

    changes: tuple[TemporalStateChange, ...]

    @property
    def count(self) -> int:
        return len(self.changes)


class TemporalStateChangeService:
    """Interpret existing temporal change assertions as state transitions.

    This service deliberately does not:
      - persist state changes;
      - create a second temporal evidence store;
      - infer missing dates;
      - resolve entities;
      - determine chronology independently;
      - overwrite source memories;
      - promote derived state changes;
      - detect conflicts.

    Conflict detection belongs to the subsequent temporal-conflict phase.
    """

    def derive(
        self,
        assertions: Iterable[TemporalChangeAssertion],
    ) -> TemporalStateChangeResult:
        changes = tuple(
            TemporalStateChange(assertion=assertion)
            for assertion in assertions
        )

        return TemporalStateChangeResult(changes=changes)

    def derive_one(
        self,
        assertion: TemporalChangeAssertion,
    ) -> TemporalStateChange:
        return TemporalStateChange(assertion=assertion)

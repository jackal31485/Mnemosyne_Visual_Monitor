"""Temporal query intent for governed hybrid retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class TemporalQueryIntent:
    """Explicit temporal constraints supplied by a retrieval query."""

    start: datetime | None = None
    end: datetime | None = None

    @property
    def has_constraint(self) -> bool:
        return self.start is not None or self.end is not None

    @property
    def is_complete_window(self) -> bool:
        return self.start is not None and self.end is not None

    def validate(self) -> None:
        """Validate that the temporal window is explicit and ordered."""

        if (self.start is None) != (self.end is None):
            raise ValueError(
                "temporal query windows require both start and end"
            )

        if (
            self.start is not None
            and self.end is not None
            and self.start > self.end
        ):
            raise ValueError(
                "temporal query start must not be after end"
            )


def build_event_date_intent(
    start: date | None,
    end: date | None,
) -> TemporalQueryIntent:
    """Build an explicit event-date query window.

    Missing dates are never inferred.
    """

    if start is None and end is None:
        return TemporalQueryIntent()

    if start is None or end is None:
        raise ValueError(
            "date_from and date_to must be supplied together"
        )

    intent = TemporalQueryIntent(
        start=datetime.combine(start, time.min),
        end=datetime.combine(end, time.max),
    )

    intent.validate()
    return intent

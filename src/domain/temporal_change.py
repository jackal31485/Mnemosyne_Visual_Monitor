from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemporalChangeAssertion:
    """Immutable explicit state-change assertion.

    This is an extraction result only. It does not persist data, resolve
    entities, infer chronology, or make governance decisions.
    """

    collective_entry_id: int
    subject_type: str
    subject_id: str
    change_type: str
    previous_state: str | None
    new_state: str
    extraction_method: str
    source_memory_id: str
    source_profile: str
    temporal_anchor: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.collective_entry_id, int)
            or isinstance(self.collective_entry_id, bool)
            or self.collective_entry_id <= 0
        ):
            raise ValueError(
                "collective_entry_id must be a positive integer"
            )

        for field_name in (
            "subject_type",
            "subject_id",
            "change_type",
            "new_state",
            "extraction_method",
            "source_memory_id",
            "source_profile",
        ):
            value = getattr(self, field_name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if self.previous_state is not None:
            if (
                not isinstance(self.previous_state, str)
                or not self.previous_state.strip()
            ):
                raise ValueError(
                    "previous_state must be a non-empty string when supplied"
                )

        if self.temporal_anchor is not None:
            if (
                not isinstance(self.temporal_anchor, str)
                or not self.temporal_anchor.strip()
            ):
                raise ValueError(
                    "temporal_anchor must be a non-empty string when supplied"
                )

        if self.change_type not in {
            "state_change",
            "replacement",
            "activation",
            "deactivation",
        }:
            raise ValueError(
                "unsupported temporal change type"
            )

"""Typed temporal assertions for Phase 11 temporal extraction.

Phase 11B.1 establishes the value-object boundary between temporal extraction
and temporal-evidence persistence.

TemporalAssertion contains temporal semantics and provenance metadata only.
It does not read source memories, perform extraction, infer chronology, or
persist itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

VALID_SUBJECT_TYPES: Final = frozenset({"memory", "entity", "relationship"})

VALID_RELATIONS: Final = frozenset({
    "at",
    "before",
    "after",
    "during",
    "overlaps",
    "meets",
    "starts",
    "ends",
    "ongoing",
})

VALID_PRECISIONS: Final = frozenset({
    "unknown",
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "second",
})

VALID_EVIDENCE_KINDS: Final = frozenset({"observed", "inferred"})


def _validate_required_text(field: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")


def _validate_positive_integer(field: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")


def _validate_enum(field: str, value: str, allowed: frozenset[str]) -> None:
    if value not in allowed:
        raise ValueError(f"invalid {field}: {value!r}")


def _validate_confidence(value: float | None) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be between 0.0 and 1.0")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def _normalize_datetime(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("temporal bounds must be non-empty text or datetime")
    return value.strip()


@dataclass(frozen=True, slots=True)
class TemporalAssertion:
    """Immutable temporal claim produced by an extraction stage."""

    collective_entry_id: int
    subject_type: str
    subject_id: str
    temporal_relation: str
    precision: str
    extraction_method: str
    source_memory_id: str
    source_profile: str
    object_type: str | None = None
    object_id: str | None = None
    start_time: str | datetime | None = None
    end_time: str | datetime | None = None
    confidence: float | None = None
    evidence_kind: str = "observed"

    def __post_init__(self) -> None:
        _validate_positive_integer(
            "collective_entry_id",
            self.collective_entry_id,
        )
        _validate_enum(
            "subject_type",
            self.subject_type,
            VALID_SUBJECT_TYPES,
        )
        _validate_required_text("subject_id", self.subject_id)
        _validate_enum(
            "temporal_relation",
            self.temporal_relation,
            VALID_RELATIONS,
        )
        _validate_enum(
            "precision",
            self.precision,
            VALID_PRECISIONS,
        )
        _validate_required_text(
            "extraction_method",
            self.extraction_method,
        )
        _validate_required_text(
            "source_memory_id",
            self.source_memory_id,
        )
        _validate_required_text(
            "source_profile",
            self.source_profile,
        )
        _validate_enum(
            "evidence_kind",
            self.evidence_kind,
            VALID_EVIDENCE_KINDS,
        )
        _validate_confidence(self.confidence)

        if (self.object_type is None) != (self.object_id is None):
            raise ValueError(
                "object_type and object_id must be supplied together"
            )

        if self.object_type is not None:
            _validate_enum(
                "object_type",
                self.object_type,
                VALID_SUBJECT_TYPES,
            )
            _validate_required_text("object_id", self.object_id)

        start_value = _normalize_datetime(self.start_time)
        end_value = _normalize_datetime(self.end_time)

        if (
            start_value is not None
            and end_value is not None
            and start_value > end_value
        ):
            raise ValueError("start_time must not be after end_time")

        if self.precision == "unknown" and (
            start_value is not None or end_value is not None
        ):
            raise ValueError(
                "unknown precision cannot carry an explicit temporal bound"
            )

        object.__setattr__(self, "start_time", start_value)
        object.__setattr__(self, "end_time", end_value)

        if self.confidence is not None:
            object.__setattr__(
                self,
                "confidence",
                float(self.confidence),
            )

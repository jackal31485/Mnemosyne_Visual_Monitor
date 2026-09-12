"""Deterministic extraction of explicit temporal expressions.

Phase 11B.2 intentionally performs only explicit temporal extraction.

The extractor:
- reads caller-supplied source text;
- identifies explicit calendar dates and simple explicit temporal phrases;
- produces immutable TemporalAssertion objects;
- never performs persistence;
- never performs governance decisions;
- never infers missing dates;
- never resolves vague relative expressions.

Governance and persistence belong to later Phase 11 stages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from src.domain.temporal_assertion import TemporalAssertion


MONTHS: Final[dict[str, int]] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTH_ABBREVIATIONS: Final[dict[str, int]] = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

MONTH_PATTERN: Final[str] = (
    r"(?:"
    + "|".join(MONTHS)
    + r"|"
    + "|".join(MONTH_ABBREVIATIONS)
    + r")"
)

FULL_DATE_RE = re.compile(
    rf"\b(?P<month>{MONTH_PATTERN})"
    r"\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:,)?\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)

NUMERIC_DATE_RE = re.compile(
    r"\b(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\b"
)

MONTH_YEAR_RE = re.compile(
    rf"\b(?P<month>{MONTH_PATTERN})\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)

YEAR_RE = re.compile(r"\b(?P<year>(?:19|20)\d{2})\b")

RANGE_RE = re.compile(
    rf"\b(?:between|from)\s+"
    rf"(?P<start>{MONTH_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,)?\s+\d{{4}}"
    rf"|\d{{4}}-\d{{1,2}}-\d{{1,2}})"
    rf"\s+(?:and|to)\s+"
    rf"(?P<end>{MONTH_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,)?\s+\d{{4}}"
    rf"|\d{{4}}-\d{{1,2}}-\d{{1,2}})\b",
    re.IGNORECASE,
)

TEMPORAL_RELATION_RE = re.compile(
    r"\b(?P<relation>before|after|during|since|until|ongoing)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class _TemporalMatch:
    start: int
    end: int
    start_time: str | None
    end_time: str | None
    precision: str
    relation: str


def _month_number(value: str) -> int:
    key = value.rstrip(".").lower()

    if key in MONTHS:
        return MONTHS[key]

    return MONTH_ABBREVIATIONS[key]


def _canonical_full_date(month: str, day: str, year: str) -> str:
    month_number = _month_number(month)
    day_number = int(day)

    try:
        value = datetime(
            int(year),
            month_number,
            day_number,
        )
    except ValueError as exc:
        raise ValueError(
            f"invalid explicit date: {month} {day}, {year}"
        ) from exc

    return value.strftime("%Y-%m-%d")


def _canonical_numeric_date(
    year: str,
    month: str,
    day: str,
) -> str:
    try:
        value = datetime(
            int(year),
            int(month),
            int(day),
        )
    except ValueError as exc:
        raise ValueError(
            f"invalid explicit date: {year}-{month}-{day}"
        ) from exc

    return value.strftime("%Y-%m-%d")


def _parse_explicit_date(text: str) -> tuple[str, str]:
    match = FULL_DATE_RE.fullmatch(text.strip())

    if match:
        return (
            _canonical_full_date(
                match.group("month"),
                match.group("day"),
                match.group("year"),
            ),
            "day",
        )

    match = NUMERIC_DATE_RE.fullmatch(text.strip())

    if match:
        return (
            _canonical_numeric_date(
                match.group("year"),
                match.group("month"),
                match.group("day"),
            ),
            "day",
        )

    match = MONTH_YEAR_RE.fullmatch(text.strip())

    if match:
        month = _month_number(match.group("month"))
        year = int(match.group("year"))

        if not 1 <= month <= 12:
            raise ValueError(f"invalid month: {month}")

        return f"{year:04d}-{month:02d}", "month"

    match = YEAR_RE.fullmatch(text.strip())

    if match:
        return match.group("year"), "year"

    raise ValueError(f"not an explicit supported date: {text!r}")


def _explicit_matches(text: str) -> list[_TemporalMatch]:
    matches: list[_TemporalMatch] = []

    def add_match(
        match: re.Match[str],
        *,
        start_time: str,
        end_time: str | None,
        precision: str,
        relation: str,
    ) -> None:
        matches.append(
            _TemporalMatch(
                start=match.start(),
                end=match.end(),
                start_time=start_time,
                end_time=end_time,
                precision=precision,
                relation=relation,
            )
        )

    # Explicit ranges claim their complete span first.
    for match in RANGE_RE.finditer(text):
        start_value, start_precision = _parse_explicit_date(
            match.group("start")
        )
        end_value, end_precision = _parse_explicit_date(
            match.group("end")
        )

        precision_order = ("year", "month", "day")
        precision = min(
            (start_precision, end_precision),
            key=precision_order.index,
        )

        add_match(
            match,
            start_time=start_value,
            end_time=end_value,
            precision=precision,
            relation="during",
        )

    def occupied(start: int, end: int) -> bool:
        return any(
            start < existing.end and end > existing.start
            for existing in matches
        )

    # Full calendar dates take precedence over month/year and bare years.
    for pattern in (FULL_DATE_RE, NUMERIC_DATE_RE):
        for match in pattern.finditer(text):
            if occupied(match.start(), match.end()):
                continue

            value, precision = _parse_explicit_date(match.group(0))

            add_match(
                match,
                start_time=value,
                end_time=None,
                precision=precision,
                relation="at",
            )

    # Month/year expressions.
    for match in MONTH_YEAR_RE.finditer(text):
        if occupied(match.start(), match.end()):
            continue

        value, precision = _parse_explicit_date(match.group(0))

        add_match(
            match,
            start_time=value,
            end_time=None,
            precision=precision,
            relation="at",
        )

    # Bare years are the least specific calendar expression.
    for match in YEAR_RE.finditer(text):
        if occupied(match.start(), match.end()):
            continue

        value, precision = _parse_explicit_date(match.group(0))

        add_match(
            match,
            start_time=value,
            end_time=None,
            precision=precision,
            relation="at",
        )

    # Explicit temporal relations without calendar bounds.
    for match in TEMPORAL_RELATION_RE.finditer(text):
        relation = match.group("relation").lower()

        if relation in {"before", "after", "during", "ongoing"}:
            matches.append(
                _TemporalMatch(
                    start=match.start(),
                    end=match.end(),
                    start_time=None,
                    end_time=None,
                    precision="unknown",
                    relation=relation,
                )
            )

    return sorted(
        matches,
        key=lambda item: (
            item.start,
            item.end,
            item.relation,
            item.start_time or "",
            item.end_time or "",
        ),
    )


class TemporalExtractor:
    """Extract explicit temporal assertions from supplied memory text."""

    def extract(
        self,
        *,
        text: str,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
        extraction_method: str = "phase11b2_explicit_temporal",
    ) -> list[TemporalAssertion]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if not text.strip():
            return []

        matches = _explicit_matches(text)

        assertions: list[TemporalAssertion] = []

        for match in matches:
            assertions.append(
                TemporalAssertion(
                    collective_entry_id=collective_entry_id,
                    subject_type="memory",
                    subject_id=source_memory_id,
                    temporal_relation=match.relation,
                    precision=match.precision,
                    extraction_method=extraction_method,
                    source_memory_id=source_memory_id,
                    source_profile=source_profile,
                    start_time=match.start_time,
                    end_time=match.end_time,
                    evidence_kind="observed",
                )
            )

        return assertions

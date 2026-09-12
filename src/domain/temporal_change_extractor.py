from __future__ import annotations

import re

from src.domain.temporal_change import TemporalChangeAssertion


_CHANGE_PATTERNS = (
    (
        re.compile(
            r"(?P<subject>[^.!?;]+?)\s+"
            r"changed\s+from\s+"
            r"(?P<previous>[^,;.!?]+?)\s+to\s+"
            r"(?P<new>[^.;!?]+)",
            re.IGNORECASE,
        ),
        "state_change",
    ),
    (
        re.compile(
            r"(?P<subject>[^.!?;]+?)\s+"
            r"was\s+(?P<previous>[^,;.!?]+?)"
            r"\s*,?\s*then\s+became\s+"
            r"(?P<new>[^.;!?]+)",
            re.IGNORECASE,
        ),
        "state_change",
    ),
    (
        re.compile(
            r"(?P<subject>[^.!?;]+?)\s+"
            r"became\s+(?P<new>[^.;!?]+)",
            re.IGNORECASE,
        ),
        "activation",
    ),
    (
        re.compile(
            r"(?P<old>[^.!?;]+?)\s+"
            r"was\s+replaced\s+by\s+"
            r"(?P<new>[^.;!?]+)",
            re.IGNORECASE,
        ),
        "replacement",
    ),
)


class TemporalChangeExtractor:
    """Deterministically extract explicit state changes.

    The extractor operates only on caller-supplied text. It deliberately
    avoids entity resolution, chronology inference, persistence, and
    governance decisions.
    """

    def extract(
        self,
        text: str,
        *,
        collective_entry_id: int,
        source_memory_id: str,
        source_profile: str,
    ) -> list[TemporalChangeAssertion]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        assertions: list[TemporalChangeAssertion] = []

        occupied_spans: list[tuple[int, int]] = []

        for pattern, change_type in _CHANGE_PATTERNS:
            for match in pattern.finditer(text):
                # More specific patterns claim their complete span first.
                # Prevent a generic "became" match from producing a second
                # assertion from an already-recognized compound transition.
                if any(
                    match.start() < end and match.end() > start
                    for start, end in occupied_spans
                ):
                    continue

                groups = match.groupdict()

                subject = (
                    groups.get("subject")
                    or groups.get("old")
                    or ""
                ).strip()

                previous = groups.get("previous")
                previous = (
                    previous.strip()
                    if previous is not None
                    else None
                )

                new_state = groups["new"].strip()

                if not subject or not new_state:
                    continue

                assertions.append(
                    TemporalChangeAssertion(
                        collective_entry_id=collective_entry_id,
                        subject_type="memory",
                        subject_id=source_memory_id,
                        change_type=change_type,
                        previous_state=previous,
                        new_state=new_state,
                        extraction_method=(
                            "explicit_state_change_v1"
                        ),
                        source_memory_id=source_memory_id,
                        source_profile=source_profile,
                    )
                )

                occupied_spans.append(
                    (match.start(), match.end())
                )

        # Remove duplicate assertions while preserving deterministic order.
        unique: dict[
            tuple[object, ...],
            TemporalChangeAssertion,
        ] = {}

        for assertion in assertions:
            key = (
                assertion.subject_type,
                assertion.subject_id,
                assertion.change_type,
                assertion.previous_state,
                assertion.new_state,
            )
            unique.setdefault(key, assertion)

        return list(unique.values())

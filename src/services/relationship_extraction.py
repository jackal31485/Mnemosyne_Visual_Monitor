"""Deterministic relationship extraction primitives for Phase 10F.

This module extracts conservative, explicitly expressed relationships
from source text. It does not resolve entities, persist relationships,
or modify source memories.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


RELATIONSHIP_EXTRACTION_METHOD = "deterministic-v1"

RELATIONSHIP_PREDICATES = (
    "uses",
    "contains",
    "part_of",
    "depends_on",
    "created_by",
    "maintained_by",
    "associated_with",
    "related_to",
    "derived_from",
    "has_profile",
    "mentions",
)


@dataclass(frozen=True)
class RelationshipCandidate:
    """A relationship candidate extracted from source text."""

    subject_mention: str
    predicate: str
    object_mention: str
    confidence: float
    relationship_kind: str
    extraction_method: str = RELATIONSHIP_EXTRACTION_METHOD


@dataclass(frozen=True)
class EntityMentionInput:
    """Entity mention supplied to the relationship extractor."""

    mention_text: str
    entity_type: str = "unknown"


@dataclass(frozen=True)
class _PredicatePattern:
    predicate: str
    pattern: re.Pattern[str]
    confidence: float


def _compile_predicate_patterns() -> tuple[_PredicatePattern, ...]:
    """Compile only the relationship language itself.

    Entity names are intentionally NOT part of these expressions. Entity
    identity is supplied independently by the mention list.
    """
    return (
        _PredicatePattern(
            "uses",
            re.compile(r"\b(?:uses|use|using|utilizes|utilises)\b", re.IGNORECASE),
            0.95,
        ),
        _PredicatePattern(
            "contains",
            re.compile(r"\b(?:contains|contain)\b", re.IGNORECASE),
            0.95,
        ),
        _PredicatePattern(
            "part_of",
            re.compile(r"\b(?:is\s+)?(?:a\s+)?part\s+of\b", re.IGNORECASE),
            0.95,
        ),
        _PredicatePattern(
            "depends_on",
            re.compile(r"\b(?:depends\s+on|depend\s+on)\b", re.IGNORECASE),
            0.95,
        ),
        _PredicatePattern(
            "created_by",
            re.compile(r"\b(?:was\s+)?created\s+by\b", re.IGNORECASE),
            0.95,
        ),
        _PredicatePattern(
            "maintained_by",
            re.compile(r"\b(?:is\s+)?maintained\s+by\b", re.IGNORECASE),
            0.95,
        ),
        _PredicatePattern(
            "associated_with",
            re.compile(r"\b(?:is\s+)?associated\s+with\b", re.IGNORECASE),
            0.90,
        ),
        _PredicatePattern(
            "related_to",
            re.compile(r"\b(?:is\s+)?related\s+to\b", re.IGNORECASE),
            0.90,
        ),
        _PredicatePattern(
            "derived_from",
            re.compile(r"\b(?:is\s+)?derived\s+from\b", re.IGNORECASE),
            0.90,
        ),
        _PredicatePattern(
            "has_profile",
            re.compile(r"\b(?:has|have)\s+(?:a\s+)?profile\b", re.IGNORECASE),
            0.90,
        ),
        _PredicatePattern(
            "mentions",
            re.compile(r"\b(?:mentions|mention)\b", re.IGNORECASE),
            0.85,
        ),
    )


_PREDICATE_PATTERNS = _compile_predicate_patterns()


def _clean_mention(value: str) -> str:
    return " ".join(value.strip().strip(".,;:!?").split())


def _mention_values(
    mentions: Iterable[EntityMentionInput | str],
) -> list[str]:
    """Return unique supplied mentions preserving first-seen spelling."""
    values: list[str] = []
    seen: set[str] = set()

    for mention in mentions:
        text = (
            mention.mention_text
            if isinstance(mention, EntityMentionInput)
            else mention
        )

        if not isinstance(text, str):
            raise TypeError("entity mentions must contain strings")

        cleaned = _clean_mention(text)

        if not cleaned:
            continue

        key = cleaned.casefold()
        if key not in seen:
            seen.add(key)
            values.append(cleaned)

    return values


def _find_mention_spans(text: str, mention: str) -> list[tuple[int, int]]:
    """Find case-insensitive whole-mention spans in source text."""
    escaped = re.escape(mention)

    # Boundaries are based on alphanumeric characters so qualified identities
    # such as agent-a:athena remain intact.
    pattern = re.compile(
        rf"(?<![\w]){escaped}(?![\w])",
        re.IGNORECASE,
    )

    return [(match.start(), match.end()) for match in pattern.finditer(text)]


def _between_is_clean(value: str) -> bool:
    """Reject relationships crossing sentence/statement boundaries."""
    return not re.search(r"[.!?;]", value)


# Phrases that explicitly weaken or infer a relationship rather than stating
# it as a fact. These are intentionally conservative. A richer inference
# classifier belongs in a later Phase 10F layer.
_INFERENCE_CUE_RE = re.compile(
    r"\b(?:"
    r"suggests?|suggesting|"
    r"implies?|implying|"
    r"indicates?|indicating|"
    r"appears?\s+to|"
    r"seems?\s+to|"
    r"probably|"
    r"possibly|"
    r"perhaps|"
    r"likely|"
    r"may|might|could"
    r")\b",
    re.IGNORECASE,
)


def _has_inference_cue(text: str, subject_span: tuple[int, int]) -> bool:
    """Return whether nearby preceding text weakens the relationship claim."""
    prefix = text[: subject_span[0]]

    # Only inspect the current sentence/statement. This prevents a cue in an
    # unrelated earlier sentence from suppressing an otherwise explicit fact.
    boundary = max(
        prefix.rfind("."),
        prefix.rfind("!"),
        prefix.rfind("?"),
        prefix.rfind(";"),
    )
    sentence_prefix = prefix[boundary + 1 :]

    return _INFERENCE_CUE_RE.search(sentence_prefix) is not None


def _extract_between(
    text: str,
    subject: str,
    object_: str,
    predicate_pattern: _PredicatePattern,
    subject_span: tuple[int, int],
    object_span: tuple[int, int],
) -> RelationshipCandidate | None:
    """Test one ordered subject/object mention pair."""
    subject_end = subject_span[1]
    object_start = object_span[0]

    if subject_end >= object_start:
        return None

    between = text[subject_end:object_start]

    if not _between_is_clean(between):
        return None

    predicate_match = predicate_pattern.pattern.search(between)

    if predicate_match is None:
        return None

    # Prevent unrelated text from being silently bridged into a relationship.
    before_predicate = between[: predicate_match.start()].strip()
    after_predicate = between[predicate_match.end() :].strip()

    if len(before_predicate.split()) > 4:
        return None

    if len(after_predicate.split()) > 4:
        return None

    return RelationshipCandidate(
        subject_mention=subject,
        predicate=predicate_pattern.predicate,
        object_mention=object_,
        confidence=predicate_pattern.confidence,
        relationship_kind="explicit",
    )


def extract_relationships(
    text: str,
    mentions: Iterable[EntityMentionInput | str],
) -> list[RelationshipCandidate]:
    """Extract conservative explicit relationships from source text.

    Only relationships whose subject and object correspond to supplied entity
    mentions are returned.

    The extractor does not infer relationships from semantic association.
    Explicit/inferred distinction is therefore preserved at the primitive
    boundary: everything returned here is explicitly expressed.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not text.strip():
        return []

    mention_values = _mention_values(mentions)

    if len(mention_values) < 2:
        return []

    spans = {
        mention: _find_mention_spans(text, mention)
        for mention in mention_values
    }

    candidates: set[RelationshipCandidate] = set()

    for subject in mention_values:
        for object_ in mention_values:
            if subject.casefold() == object_.casefold():
                continue

            for subject_span in spans[subject]:
                if _has_inference_cue(text, subject_span):
                    continue

                for object_span in spans[object_]:
                    for predicate_pattern in _PREDICATE_PATTERNS:
                        candidate = _extract_between(
                            text,
                            subject,
                            object_,
                            predicate_pattern,
                            subject_span,
                            object_span,
                        )

                        if candidate is not None:
                            candidates.add(candidate)

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.subject_mention.casefold(),
            candidate.predicate,
            candidate.object_mention.casefold(),
        ),
    )

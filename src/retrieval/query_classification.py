"""Deterministic query classification for Phase 15 retrieval routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class QueryIntent(str, Enum):
    """Supported retrieval intents."""

    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    TEMPORAL = "temporal"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class QueryClassification:
    """Routing metadata produced from a normalized retrieval query."""

    intent: QueryIntent
    normalized_query: str
    signals: tuple[str, ...]


class QueryClassifier:
    """Classify retrieval queries without making authorization decisions."""

    _TEMPORAL_PATTERNS = (
        r"\bwhen\b",
        r"\bdate\b",
        r"\bdated\b",
        r"\byear\b",
        r"\bmonth\b",
        r"\bday\b",
        r"\bbefore\b",
        r"\bafter\b",
        r"\bduring\b",
        r"\bsince\b",
        r"\buntil\b",
        r"\brecent(?:ly)?\b",
        r"\blast\s+(?:week|month|year)\b",
        r"\bthis\s+(?:week|month|year)\b",
    )

    _ENTITY_PATTERNS = (
        r"\bwho\s+is\b",
        r"\bwhat\s+is\s+(?:the\s+)?(?:person|entity|project|company|team)\b",
        r"\bentity\b",
        r"\bperson\b",
        r"\bprofile\b",
        r"\babout\s+[A-Z][\w-]*\b",
    )

    _RELATIONSHIP_PATTERNS = (
        r"\brelationship\b",
        r"\brelated\s+to\b",
        r"\bconnected\s+to\b",
        r"\bconnection\b",
        r"\bbetween\s+.+\s+and\s+.+\b",
        r"\bdepends\s+on\b",
        r"\bassociated\s+with\b",
        r"\blink(?:ed)?\s+to\b",
    )

    _LEXICAL_PATTERNS = (
        r"\bexact(?:ly)?\b",
        r"\bexact\s+match\b",
        r"\bverbatim\b",
        r"\bphrase\b",
        r"\bkeyword\b",
        r"\bcontains?\b",
        r"\bliteral(?:ly)?\b",
    )

    @staticmethod
    def normalize(query: str) -> str:
        """Normalize whitespace while preserving query content."""

        if not isinstance(query, str):
            raise TypeError("query must be a string")

        normalized = re.sub(r"\s+", " ", query).strip()

        if not normalized:
            raise ValueError("query must not be empty")

        return normalized

    @classmethod
    def _matches(
        cls,
        query: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(
            re.search(pattern, query, flags=re.IGNORECASE)
            for pattern in patterns
        )

    @classmethod
    def classify(cls, query: str) -> QueryClassification:
        """Return deterministic routing metadata for a retrieval query."""

        normalized_query = cls.normalize(query)

        temporal = cls._matches(
            normalized_query,
            cls._TEMPORAL_PATTERNS,
        )
        entity = cls._matches(
            normalized_query,
            cls._ENTITY_PATTERNS,
        )
        relationship = cls._matches(
            normalized_query,
            cls._RELATIONSHIP_PATTERNS,
        )
        lexical = cls._matches(
            normalized_query,
            cls._LEXICAL_PATTERNS,
        )

        signals: list[str] = []

        if lexical:
            signals.append(QueryIntent.LEXICAL.value)

        if temporal:
            signals.append(QueryIntent.TEMPORAL.value)

        if entity:
            signals.append(QueryIntent.ENTITY.value)

        if relationship:
            signals.append(QueryIntent.RELATIONSHIP.value)

        if len(signals) > 1:
            intent = QueryIntent.HYBRID
        elif lexical:
            intent = QueryIntent.LEXICAL
        elif temporal:
            intent = QueryIntent.TEMPORAL
        elif entity:
            intent = QueryIntent.ENTITY
        elif relationship:
            intent = QueryIntent.RELATIONSHIP
        else:
            intent = QueryIntent.SEMANTIC

        return QueryClassification(
            intent=intent,
            normalized_query=normalized_query,
            signals=tuple(signals),
        )


def classify_query(query: str) -> QueryClassification:
    """Convenience wrapper for query classification."""

    return QueryClassifier.classify(query)

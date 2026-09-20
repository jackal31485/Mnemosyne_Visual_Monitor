"""Deterministic multilingual retrieval capability handling for Phase 15E.

This module does not perform language translation, transliteration, or model
selection. It describes what the existing retrieval stack can safely claim
for a query and provides deterministic normalization/capability decisions.

The production semantic encoder is all-MiniLM-L6-v2, which is treated as
English-compatible only. Unicode lexical retrieval remains available for
queries outside that semantic capability boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import unicodedata


class QueryScript(str, Enum):
    """Coarse script profile used for retrieval capability decisions."""

    LATIN = "latin"
    NON_LATIN = "non_latin"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class SemanticCapability(str, Enum):
    """Semantic retrieval capability of the installed model."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class MultilingualRetrievalProfile:
    """Deterministic retrieval capability metadata for one query."""

    normalized_query: str
    script: QueryScript
    semantic_capability: SemanticCapability
    lexical_supported: bool
    semantic_reason: str


def normalize_multilingual_query(query: str) -> str:
    """Normalize Unicode safely while preserving the query's characters."""

    if not isinstance(query, str):
        raise TypeError("query must be a string")

    normalized = unicodedata.normalize("NFKC", query)
    normalized = " ".join(normalized.split())

    if not normalized:
        raise ValueError("query must not be empty")

    return normalized


def _is_latin_letter(character: str) -> bool:
    if not character.isalpha():
        return False

    name = unicodedata.name(character, "")
    return "LATIN" in name


def classify_query_script(query: str) -> QueryScript:
    """Classify the query by Unicode letter script.

    This intentionally does not claim to identify a natural language.
    """

    normalized = normalize_multilingual_query(query)

    has_latin = False
    has_non_latin = False

    for character in normalized:
        if not character.isalpha():
            continue

        if _is_latin_letter(character):
            has_latin = True
        else:
            has_non_latin = True

    if has_latin and has_non_latin:
        return QueryScript.MIXED

    if has_latin:
        return QueryScript.LATIN

    if has_non_latin:
        return QueryScript.NON_LATIN

    return QueryScript.UNKNOWN


def build_multilingual_profile(query: str) -> MultilingualRetrievalProfile:
    """Build deterministic capability metadata for a retrieval query."""

    normalized = normalize_multilingual_query(query)
    script = classify_query_script(normalized)

    if script is QueryScript.NON_LATIN:
        capability = SemanticCapability.UNSUPPORTED
        reason = (
            "installed all-MiniLM-L6-v2 semantic encoder is "
            "English-compatible only"
        )
    elif script is QueryScript.MIXED:
        capability = SemanticCapability.UNSUPPORTED
        reason = (
            "mixed-script query is outside the validated semantic "
            "capability boundary of all-MiniLM-L6-v2"
        )
    else:
        capability = SemanticCapability.SUPPORTED
        reason = (
            "query is within the validated Latin-script capability "
            "boundary of all-MiniLM-L6-v2"
        )

    return MultilingualRetrievalProfile(
        normalized_query=normalized,
        script=script,
        semantic_capability=capability,
        lexical_supported=True,
        semantic_reason=reason,
    )

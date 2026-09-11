"""Deterministic entity mention extraction for Mnemosyne Phase 10B.

The first extractor is intentionally conservative and dependency-free.

It produces entity *mentions* only.  It never creates or resolves canonical
entities and never modifies source memory databases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


EXTRACTION_METHOD = "deterministic-v1"

# Common technical/project markers already used throughout the project.
_TECHNOLOGY_PATTERNS = (
    r"\b(?:Python|SQLite|FastAPI|Uvicorn|OpenCV|Linux|Ubuntu|Git|Forgejo)\b",
    r"\b(?:BM25|RRF|FTS5|NLP|API|HTTP|JSON|SQL)\b",
    r"\b(?:GPT-\d+(?:\.\d+)?|Qwen\d*|Devstral|Horus|Athena|Mnemosyne|Hermes)\b",
)

# Capitalized multi-word phrases are useful as conservative candidate
# extraction without requiring an NLP model.
_PROPER_PHRASE_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*)+\b"
)

_SINGLE_TECH_RE = re.compile(
    "|".join(_TECHNOLOGY_PATTERNS),
    re.IGNORECASE,
)

_ENTITY_TYPES = {
    "technology",
    "project",
}


@dataclass(frozen=True)
class EntityMention:
    """One extracted entity mention."""

    mention_text: str
    entity_type: str
    confidence: float
    extraction_method: str = EXTRACTION_METHOD


class DeterministicEntityExtractor:
    """Extract conservative, reproducible entity mentions from text."""

    def extract(self, content: str) -> list[EntityMention]:
        if not isinstance(content, str):
            raise TypeError("content must be a string")

        if not content.strip():
            return []

        candidates: list[EntityMention] = []
        seen: set[tuple[str, str]] = set()

        def add(
            mention_text: str,
            entity_type: str,
            confidence: float,
        ) -> None:
            normalized = " ".join(mention_text.split()).strip()
            if not normalized:
                return

            key = (normalized.casefold(), entity_type)
            if key in seen:
                return

            seen.add(key)
            candidates.append(
                EntityMention(
                    mention_text=normalized,
                    entity_type=entity_type,
                    confidence=confidence,
                )
            )

        for match in _SINGLE_TECH_RE.finditer(content):
            text = match.group(0).strip()
            add(text, "technology", 0.95)

        for match in _PROPER_PHRASE_RE.finditer(content):
            text = match.group(0).strip()

            # Avoid treating ordinary sentence openings as entities.
            words = text.split()
            if len(words) < 2:
                continue

            if text.casefold() in {
                "The Phase",
                "This Project",
                "The System",
                "The User",
            }:
                continue

            add(text, "project", 0.65)

        candidates.sort(
            key=lambda item: (
                item.mention_text.casefold(),
                item.entity_type,
            )
        )

        return candidates

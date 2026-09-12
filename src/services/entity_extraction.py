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

_SINGLE_TECH_RE = re.compile(
    "|".join(_TECHNOLOGY_PATTERNS),
    re.IGNORECASE,
)

# Project names are extracted only when a project-like marker explicitly
# identifies the phrase as a project.  We intentionally do not treat every
# capitalized multi-word phrase as a project because collective memories
# contain instructions, headings, status messages, and prose with many
# capitalized fragments.
_PROJECT_AFTER_MARKER_RE = re.compile(
    r"\b(?:project|repository|application|codebase)"
    r"\s+(?:named\s+|called\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){1,5})"
)

_PROJECT_BEFORE_MARKER_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){1,5})"
    r"\s+(?:project|repository|application|codebase)\b"
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

        project_candidates: list[str] = []

        for match in _PROJECT_AFTER_MARKER_RE.finditer(content):
            project_candidates.append(match.group(1))

        for match in _PROJECT_BEFORE_MARKER_RE.finditer(content):
            project_candidates.append(match.group(1))

        for text in project_candidates:
            normalized = " ".join(text.split()).strip()

            # Remove a leading grammatical article captured by the
            # before-marker pattern, e.g. "The Mnemosyne Visual Monitor".
            normalized = re.sub(
                r"^(?:the|a|an)\s+",
                "",
                normalized,
                flags=re.IGNORECASE,
            )

            # A single-word name is too ambiguous to classify as a project
            # from a generic marker alone.  It may already be a technology
            # or product/entity name, such as "Mnemosyne project".
            if len(normalized.split()) < 2:
                continue

            # Defensive filtering for fragments that can occur immediately
            # around project-like markers but are not project names.
            if normalized.casefold() in {
                "the project",
                "this project",
                "the repository",
                "this repository",
                "the application",
                "this application",
                "the codebase",
                "this codebase",
            }:
                continue

            # Reject generic instruction/document scaffolding that can otherwise
            # satisfy the capitalization-based project-name pattern.
            project_noise_words = {
                "all",
                "current",
                "local",
                "location",
                "repository",
                "state",
                "the",
            }
            normalized_words = {
                word.casefold()
                for word in normalized.split()
            }

            if normalized_words & project_noise_words:
                continue

            add(normalized, "project", 0.90)

        candidates.sort(
            key=lambda item: (
                item.mention_text.casefold(),
                item.entity_type,
            )
        )

        return candidates

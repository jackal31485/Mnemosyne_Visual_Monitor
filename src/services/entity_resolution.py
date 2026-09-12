"""Deterministic, governed entity resolution for Mnemosyne Phase 10D.

This resolver generates candidates from existing canonical entities and
records explicit resolution decisions.  It never silently creates, merges,
renames, or modifies canonical entities.

The first implementation intentionally uses conservative normalized-name
matching.  More advanced similarity and contextual resolution can be added
later without changing the persistence contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import uuid
import unicodedata

from src.domain.entities import EntityDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO


RESOLUTION_METHOD = "normalized-name-v1"

_DECISION_SAME_ENTITY = "same_entity"
_DECISION_NEW_ENTITY = "new_entity"
_DECISION_AMBIGUOUS = "ambiguous"
_DECISION_UNRESOLVED = "unresolved"

RESOLUTION_NAMESPACE = uuid.UUID(
    "3c8f2b91-5e47-4a6d-b8f1-2d9c7e4a6135"
)


def _stable_resolution_id(mention_id: str) -> str:
    """Return a deterministic identity for one mention's resolution."""
    return str(uuid.uuid5(RESOLUTION_NAMESPACE, mention_id))


@dataclass(frozen=True)
class EntityCandidate:
    """One canonical entity considered for a mention."""

    entity_id: str
    canonical_name: str
    entity_type: str
    score: float


@dataclass(frozen=True)
class EntityResolutionResult:
    """The deterministic resolution result for one mention."""

    mention_id: str
    decision: str
    confidence: float
    proposed_entity_id: str | None
    candidates: tuple[EntityCandidate, ...]


def normalize_entity_name(value: str) -> str:
    """Normalize an entity name for conservative comparison.

    Matching is case-insensitive and punctuation/whitespace tolerant.
    No semantic stemming, synonym expansion, or token-only matching occurs.
    """

    if not isinstance(value, str):
        raise TypeError("value must be a string")

    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(
        character if character.isalnum() else " "
        for character in value
    )
    return " ".join(value.split())


def generate_candidates(
    mention: dict,
    entity_dao: EntityDAO,
) -> tuple[EntityCandidate, ...]:
    """Generate exact normalized-name candidates of the same entity type."""

    normalized_mention = normalize_entity_name(mention["mention_text"])

    if not normalized_mention:
        return ()

    candidates: list[EntityCandidate] = []

    for entity in entity_dao.list(
        entity_type=mention["entity_type"],
        status="active",
    ):
        if normalize_entity_name(entity["canonical_name"]) != normalized_mention:
            continue

        candidates.append(
            EntityCandidate(
                entity_id=entity["entity_id"],
                canonical_name=entity["canonical_name"],
                entity_type=entity["entity_type"],
                score=1.0,
            )
        )

    candidates.sort(
        key=lambda candidate: candidate.entity_id,
    )

    return tuple(candidates)


def resolve_mention(
    mention: dict,
    entity_dao: EntityDAO,
) -> EntityResolutionResult:
    """Resolve one mention against existing active canonical entities.

    This function performs no persistence and never modifies EntityDAO.
    """

    mention_id = mention.get("mention_id")
    if not isinstance(mention_id, str) or not mention_id.strip():
        raise ValueError("mention must contain a valid mention_id")

    candidates = generate_candidates(mention, entity_dao)

    if len(candidates) == 1:
        candidate = candidates[0]
        return EntityResolutionResult(
            mention_id=mention_id,
            decision=_DECISION_SAME_ENTITY,
            confidence=1.0,
            proposed_entity_id=candidate.entity_id,
            candidates=candidates,
        )

    if len(candidates) > 1:
        return EntityResolutionResult(
            mention_id=mention_id,
            decision=_DECISION_AMBIGUOUS,
            confidence=0.0,
            proposed_entity_id=None,
            candidates=candidates,
        )

    return EntityResolutionResult(
        mention_id=mention_id,
        decision=_DECISION_NEW_ENTITY,
        confidence=1.0,
        proposed_entity_id=None,
        candidates=(),
    )


def resolve_and_record(
    mention_dao: EntityMentionDAO,
    entity_dao: EntityDAO,
    resolution_dao: EntityResolutionDAO,
    *,
    mention_id: str,
) -> EntityResolutionResult:
    """Resolve one mention and persist its explicit decision.

    The existing entity table is read-only from this service's perspective.
    A duplicate resolution is rejected by EntityResolutionDAO rather than
    silently replacing an earlier decision.
    """

    mention = mention_dao.get(mention_id)

    if mention is None:
        raise KeyError(f"entity mention not found: {mention_id}")

    result = resolve_mention(mention, entity_dao)

    evidence = {
        "mention_id": mention_id,
        "candidate_entity_ids": [
            candidate.entity_id
            for candidate in result.candidates
        ],
    }

    resolution_dao.create(
        mention_id=mention_id,
        proposed_entity_id=result.proposed_entity_id,
        decision=result.decision,
        confidence=result.confidence,
        resolution_method=RESOLUTION_METHOD,
        evidence=evidence,
        resolution_id=_stable_resolution_id(mention_id),
    )

    return result

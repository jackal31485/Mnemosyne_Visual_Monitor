"""Batch service for governed deterministic entity resolution."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from src.domain.entities import EntityDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.services.entity_resolution import RESOLUTION_METHOD, resolve_mention


@dataclass(frozen=True)
class EntityResolutionFailure:
    mention_id: str
    error: str


@dataclass(frozen=True)
class EntityResolutionReport:
    processed: int
    resolutions_created: int
    resolutions_existing: int
    skipped: int
    failures: tuple[EntityResolutionFailure, ...]


def resolve_entities(
    mention_dao: EntityMentionDAO,
    entity_dao: EntityDAO,
    resolution_dao: EntityResolutionDAO,
) -> EntityResolutionReport:
    """Resolve all mentions without an existing resolution.

    Existing decisions are preserved. Canonical entities are never modified
    or created by this service.
    """

    processed = 0
    resolutions_created = 0
    resolutions_existing = 0
    skipped = 0
    failures: list[EntityResolutionFailure] = []

    for mention in mention_dao.list():
        mention_id = mention["mention_id"]

        if resolution_dao.get_for_mention(mention_id) is not None:
            resolutions_existing += 1
            continue

        processed += 1

        try:
            result = resolve_mention(mention, entity_dao)

            resolution_dao.create(
                mention_id=mention_id,
                proposed_entity_id=result.proposed_entity_id,
                decision=result.decision,
                confidence=result.confidence,
                resolution_method=RESOLUTION_METHOD,
                evidence={
                    "mention_id": mention_id,
                    "source_profile": mention["source_profile"],
                    "source_memory_id": mention["source_memory_id"],
                    "collective_entry_id": mention["collective_entry_id"],
                    "candidate_entity_ids": [
                        candidate.entity_id
                        for candidate in result.candidates
                    ],
                },
            )

            resolutions_created += 1

        except (KeyError, ValueError, TypeError, sqlite3.Error, OSError) as exc:
            failures.append(
                EntityResolutionFailure(
                    mention_id=mention_id,
                    error=str(exc),
                )
            )
            skipped += 1

    return EntityResolutionReport(
        processed=processed,
        resolutions_created=resolutions_created,
        resolutions_existing=resolutions_existing,
        skipped=skipped,
        failures=tuple(failures),
    )
